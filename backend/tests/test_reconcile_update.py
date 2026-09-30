"""After an update of the hub, each user's history is reconciled once."""

from __future__ import annotations

from typing import Any

import pytest
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models.user import User
from app.services import reconcile, reconcile_update
from httpx import AsyncClient
from sqlalchemy import select

VERSION = "a1b2c3d"


@pytest.fixture
def new_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """The hub runs a known version (GIT_COMMIT)."""
    monkeypatch.setattr(get_settings(), "git_commit", VERSION)


async def _stamps() -> dict[str, str | None]:
    async with SessionFactory() as session:
        rows = await session.execute(select(User.email, User.reconciled_commit))
        return dict(rows.tuples().all())


async def test_each_user_once_per_version(
    client: AsyncClient, member: dict[str, str], new_version: None
) -> None:
    assert await reconcile_update.run_pending(SessionFactory) == 2
    assert set((await _stamps()).values()) == {VERSION}
    # the hourly check finds nothing more to do for this version
    assert await reconcile_update.run_pending(SessionFactory) == 0


async def test_a_reconcile_by_hand_counts_too(
    client: AsyncClient, auth: dict[str, str], new_version: None
) -> None:
    async with SessionFactory() as session:
        admin = await session.scalar(select(User.id))
        assert admin is not None
        report = await reconcile.run(session, admin)
    assert report["seconds"] >= 0 and isinstance(report["slowest"], list)
    async with SessionFactory() as session:
        assert await reconcile_update.pending(session) == []


async def test_a_failure_is_tried_again_and_spares_the_others(
    client: AsyncClient,
    member: dict[str, str],
    new_version: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = reconcile.run

    async def fails_for_member(session: Any, user_id: str) -> Any:
        user = await session.get(User, user_id)
        if user.email == "membre@example.com":
            raise RuntimeError("base indisponible")
        return await real(session, user_id)

    monkeypatch.setattr(reconcile, "run", fails_for_member)
    assert await reconcile_update.run_pending(SessionFactory) == 1
    stamps = await _stamps()
    assert stamps["membre@example.com"] is None  # tried again next hour
    assert VERSION in stamps.values()


async def test_nothing_without_a_version_or_when_turned_off(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "git_commit", "")
    assert await reconcile_update.run_pending(SessionFactory) == 0
    monkeypatch.setattr(get_settings(), "git_commit", VERSION)
    monkeypatch.setattr(get_settings(), "reconcile_after_update", False)
    assert await reconcile_update.run_pending(SessionFactory) == 0
