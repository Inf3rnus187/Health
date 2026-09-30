"""Speed-ups that must give the same answers as the plain way."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.core.db import SessionFactory
from app.models.work import Evidence
from app.services import metric_memo, metric_overview, metrics, work_context
from app.services.timed_entries import utc
from httpx import AsyncClient

PARIS = ZoneInfo("Europe/Paris")


def _items() -> list[Evidence]:
    """Proofs at every hour of four days, some of them stays."""
    first = datetime(2026, 3, 27, tzinfo=UTC)  # a change of hour inside
    out = []
    for i in range(96):
        at = first + timedelta(hours=i * 1.1)
        stay = at + timedelta(days=i % 3) if i % 7 == 0 else None
        out.append(Evidence(id=f"e{i}", kind="taxi", occurred_at=at,
                            ended_at=stay, title=f"Trace test {i}",
                            time_known=True))  # fmt: skip
    return out


def _plain(items: list[Evidence], day: date, wanted: str) -> list[str]:
    """Every proof read against the day (the former way)."""
    found = []
    for item in items:
        at = utc(item.occurred_at).astimezone(PARIS)
        end = utc(item.ended_at).astimezone(PARIS) if item.ended_at else None
        morning = wanted == "end" and at.date() == day + timedelta(1)
        covers = end is not None and at.date() <= day <= end.date()
        if at.date() == day or (morning and at.hour < 12) or covers:
            found.append((at.isoformat(), item.id))
    return [key for _, key in sorted(found, key=lambda f: f[0])]


@pytest.mark.parametrize("wanted", ["start", "end"])
def test_proofs_by_day_are_the_plain_reading(wanted: str) -> None:
    items = _items()
    index = work_context._by_day(items, PARIS)
    for offset in range(-1, 7):
        day = date(2026, 3, 27) + timedelta(days=offset)
        seen = work_context._seen(index, day, wanted)
        assert [s["id"] for s in seen] == _plain(items, day, wanted)


async def _user(client: AsyncClient, auth: dict[str, str]) -> str:
    return str((await client.get("/api/v1/auth/me", headers=auth)).json()["id"])


async def test_a_session_reads_a_metric_once_and_again_after_rollback(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    async with SessionFactory() as session:
        weight = await metrics.get_metric(session, "body.weight")
        assert await metrics.get_metric(session, "body.weight") is weight
        found = await metrics.prefetch(
            session, ["body.weight", "habit.cigarettes", "absent.key"]
        )
        assert set(found) == {"body.weight", "habit.cigarettes"}
        assert found["body.weight"] is weight
        await session.rollback()  # expires what the session read
        assert "body.weight" not in metric_memo.seen(session)
        again = await metrics.get_metric(session, "body.weight")
        assert again.key == "body.weight"


async def test_overviews_read_together_equal_one_by_one(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    items: list[dict[str, Any]] = [
        {"metric_key": key, "date_key": f"2026-09-{day:02d}", "value": value}
        for key, days, value in (
            ("body.weight", (1, 10, 20), 106.5),
            ("habit.coffee", (3, 4, 28), 2),
            ("habit.cigarettes", (28,), 61),
        )
        for day in days
    ]
    made = await client.post(
        "/api/v1/measurements", json={"items": items}, headers=auth
    )
    assert made.status_code == 201
    user_id = await _user(client, auth)
    keys = ["body.weight", "habit.coffee", "habit.cigarettes", "absent.key"]
    async with SessionFactory() as session:
        together = await metric_overview.overviews(session, user_id, keys, 30)
    assert set(together) == set(keys) - {"absent.key"}
    for key in together:
        async with SessionFactory() as session:
            alone = await metric_overview.overview(session, user_id, key, 30)
        assert together[key] == alone
    assert together["body.weight"]["days_count"] == 3


async def test_overviews_stay_with_their_user(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    item = {"metric_key": "body.weight", "date_key": "2026-09-01", "value": 99}
    await client.post(
        "/api/v1/measurements", json={"items": [item]}, headers=auth
    )
    member_id = await _user(client, member)
    async with SessionFactory() as session:
        theirs = await metric_overview.overviews(
            session, member_id, ["body.weight"], 30
        )
    assert theirs["body.weight"]["latest"] is None  # the other's weight
