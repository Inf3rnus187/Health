"""The inventory's counts stay exact through every kind of write."""

from __future__ import annotations

from typing import Any

from app.core.db import SessionFactory, engine
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.services import sample_counts
from httpx import AsyncClient
from sqlalchemy import delete, func, select, update

URL = "/api/v1/sync/healthkit"
Q = "HKQuantityTypeIdentifier"


def _hr(uuid: str, day: str, bpm: float = 60) -> dict[str, Any]:
    at = f"{day}T08:00:00+02:00"
    return {"uuid": uuid, "type": f"{Q}HeartRate", "start": at, "end": at,
            "value": bpm, "unit": "count/min"}  # fmt: skip


async def _app(client: AsyncClient, headers: dict[str, str]) -> dict[str, str]:
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "App iPhone", "scopes": ["write:measurements"]},
        headers=headers,
    )
    return {"Authorization": f"Bearer {made.json()['token']}"}


async def _truth() -> list[tuple[Any, ...]]:
    """Every group counted from the samples themselves."""
    async with SessionFactory() as session:
        rows = await session.execute(
            select(
                HealthSample.user_id,
                HealthSample.metric_id,
                HealthSample.source,
                func.count(),
                func.min(HealthSample.start_at),
                func.max(HealthSample.start_at),
            ).group_by(
                HealthSample.user_id,
                HealthSample.metric_id,
                HealthSample.source,
            )
        )
        return sorted(_plain(r) for r in rows.all())


async def _kept() -> list[tuple[Any, ...]]:
    """Every group as the counts table holds it."""
    async with SessionFactory() as session:
        rows = await session.execute(select(sample_counts.counts))
        return sorted(_plain(r) for r in rows.all())


def _plain(row: Any) -> tuple[Any, ...]:
    user, metric, source, n, first, last = row
    day = lambda v: str(v)[:19]  # noqa: E731 - same text on both dialects
    return (user, metric, source, int(n), day(first), day(last))


async def test_counts_follow_inserts_replacements_moves_and_deletes(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    mine, theirs = await _app(client, auth), await _app(client, member)
    days = ["2026-09-20", "2026-09-22", "2026-09-24"]
    batch = [_hr(f"A{i}", d) for i, d in enumerate(days)]
    await client.post(URL, json={"samples": batch}, headers=mine)
    await client.post(URL, json={"samples": [_hr("B1", days[1])]},
                      headers=theirs)  # fmt: skip
    assert await _kept() == await _truth() != []
    # the first one sent again, a day earlier: the first date moves
    moved = {"samples": [_hr("A0", "2026-09-10", 70)]}
    await client.post(URL, json=moved, headers=mine)
    assert await _kept() == await _truth()
    # the last one deleted: the last date goes back
    await client.post(URL, json={"deleted": ["A2"]}, headers=mine)
    assert await _kept() == await _truth()
    async with SessionFactory() as session:  # a merge moves a metric
        other = await session.scalar(
            select(MetricDefinition.id).where(
                MetricDefinition.key == "heart.hrv"
            )
        )
        await session.execute(
            update(HealthSample)
            .where(HealthSample.external_id == "A1")
            .values(metric_id=other, source="autre")
        )
        await session.commit()
    assert await _kept() == await _truth()
    async with SessionFactory() as session:  # a bulk delete
        await session.execute(delete(HealthSample))
        await session.commit()
    assert await _kept() == [] == await _truth()


async def test_a_rebuild_finds_the_same_and_each_user_sees_theirs(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    mine, theirs = await _app(client, auth), await _app(client, member)
    await client.post(URL, json={"samples": [_hr("C1", "2026-09-01")]},
                      headers=mine)  # fmt: skip
    await client.post(URL, json={"samples": [_hr("D1", "2026-09-02"),
                                             _hr("D2", "2026-09-03")]},
                      headers=theirs)  # fmt: skip
    before = await _kept()
    me = (await client.get("/api/v1/auth/me", headers=auth)).json()["id"]
    async with SessionFactory() as session:
        await sample_counts.rebuild(session, me)
        await session.commit()
    assert await _kept() == before == await _truth()
    for headers, count in ((auth, 1), (member, 2)):
        rows = (
            await client.get("/api/v1/data/inventory", headers=headers)
        ).json()
        (hr,) = (r for r in rows if r["key"] == "heart.rate")
        assert [s["count"] for s in hr["raw"]] == [count]


async def test_an_account_deleted_takes_its_counts(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    theirs = await _app(client, member)
    await client.post(URL, json={"samples": [_hr("E1", "2026-09-05")]},
                      headers=theirs)  # fmt: skip
    assert await _kept() != []
    gone = await client.delete("/api/v1/me", headers=member)
    assert gone.status_code == 200, gone.text
    assert await _kept() == await _truth()
    if engine.dialect.name == "postgresql":  # SQLite here: no cascade
        assert await _kept() == []
