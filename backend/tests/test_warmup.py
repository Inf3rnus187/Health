"""The API's warm-up when a process starts: a sync's reads, nothing written."""

from __future__ import annotations

from typing import Any

import pytest
from app.core.config import get_settings
from app.core.db import SessionFactory, engine
from app.services import healthkit_sync, sample_writes, warmup
from httpx import AsyncClient
from sqlalchemy import event, text
from structlog.testing import capture_logs

_TABLES = (
    "users",
    "api_tokens",
    "metric_definitions",
    "health_samples",
    "sample_counts",
    "measurements",
    "workouts",
    "audit_log",
)
_WRITES = {"INSERT", "UPDATE", "DELETE", "COPY", "TRUNCATE"}


async def _counts() -> dict[str, int]:
    async with SessionFactory() as session:
        return {
            table: (
                await session.execute(text(f"SELECT count(*) FROM {table}"))  # noqa: S608
            ).scalar_one()
            for table in _TABLES
        }


async def _statements(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The SQL the warm-up sends (a COPY fails the test at once)."""
    seen: list[str] = []

    def _seen(*args: Any) -> None:
        seen.append(args[2])

    async def _no_copy(*args: Any) -> None:
        raise AssertionError("a COPY during the warm-up")

    monkeypatch.setattr(sample_writes, "write", _no_copy)
    event.listen(engine.sync_engine, "before_cursor_execute", _seen)
    try:
        await warmup.run()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _seen)
    return seen


async def test_the_warmup_reads_and_writes_nothing(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real data first: after the warm-up, every table holds the same."""
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "App", "scopes": ["write:measurements"]},
        headers=auth,
    )
    app = {"Authorization": f"Bearer {made.json()['token']}"}
    sample = {
        "uuid": "W1", "type": "HKQuantityTypeIdentifierHeartRate",
        "start": "2026-09-26T08:00:00+02:00", "value": 61, "unit": "count/min",
    }  # fmt: skip
    sent = await client.post(
        "/api/v1/sync/healthkit", json={"samples": [sample]}, headers=app
    )
    assert sent.status_code == 200, sent.text
    before = await _counts()
    with capture_logs() as logs:
        seen = await _statements(monkeypatch)
    written = [sql for sql in seen if sql.split()[0].upper() in _WRITES]
    assert written == []
    assert any("health_samples" in sql for sql in seen)  # it did read
    assert any("api_tokens" in sql for sql in seen)
    assert await _counts() == before
    assert [log["event"] for log in logs] == ["warmed"]


async def test_a_failed_warmup_never_stops_the_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _broken(*args: Any) -> None:
        raise RuntimeError("base injoignable")

    monkeypatch.setattr(healthkit_sync, "warm", _broken)
    with capture_logs() as logs:
        await warmup.run()  # no exception
    assert [log["event"] for log in logs] == ["warmup_failed"]


async def test_the_warmup_can_be_turned_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "api_warmup", False)
    assert await _statements(monkeypatch) == []
