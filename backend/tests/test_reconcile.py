"""One truth: canonical keys, daily values rebuilt from raw samples."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.core.db import SessionFactory
from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.user import User
from app.services import reconcile
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import QUANTITY_SPECS, MetricSpec
from httpx import AsyncClient
from sqlalchemy import select

_WEIGHT = QUANTITY_SPECS["HKQuantityTypeIdentifierBodyMass"]
_STEPS = QUANTITY_SPECS["HKQuantityTypeIdentifierStepCount"]


async def _user_id() -> str:
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalars().first()
        assert user is not None
        return user.id


async def _samples(
    spec: MetricSpec, rows: list[tuple[datetime, float, str, str]]
) -> str:
    """Insert raw samples ``(time, value, unit, source)``; metric id."""
    user_id = await _user_id()
    async with SessionFactory() as session:
        metric_id = await MetricCache().id_for(session, spec)
        for at, value, unit, source in rows:
            session.add(
                HealthSample(
                    id=new_uuid(),
                    user_id=user_id,
                    metric_id=metric_id,
                    start_at=at,
                    value_num=value,
                    unit=unit,
                    source=source,
                    created_at=utcnow(),
                )
            )
        await session.commit()
    return metric_id


async def _daily(metric_id: str) -> dict[date, Measurement]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Measurement).where(Measurement.metric_id == metric_id)
        )
        return {m.date_key: m for m in result.scalars().all()}


async def _reconcile() -> dict:
    async with SessionFactory() as session:
        return await reconcile.run(session, await _user_id())


async def test_rebuild_restores_missing_days_in_kg() -> None:
    """Raw weigh-ins present but daily values missing (interrupted import)."""
    start = datetime(2026, 6, 1, 7, 30, tzinfo=UTC)
    rows = [
        (start + timedelta(days=i), 220.0 - i, "lb", "apple") for i in range(20)
    ]
    metric_id = await _samples(_WEIGHT, rows)
    report = await _reconcile()
    assert report["days"] == 20
    daily = await _daily(metric_id)
    assert len(daily) == 20
    assert daily[date(2026, 6, 1)].value_num == pytest.approx(99.79, abs=0.01)


async def test_one_healthkit_channel_per_day() -> None:
    """Native + Health Auto Export carry the same steps: never add them."""
    day = datetime(2026, 6, 2, 8, 0, tzinfo=UTC)
    native = [
        (day + timedelta(hours=h), 100.0, "count", "apple") for h in range(10)
    ]
    partial = [
        (day + timedelta(hours=h), 100.0, "count", "auto-export")
        for h in range(4)
    ]
    metric_id = await _samples(_STEPS, native + partial)
    await _reconcile()
    row = (await _daily(metric_id))[date(2026, 6, 2)]
    assert row.value_num == 1000
    assert row.source == "apple"


async def test_later_manual_weigh_in_is_kept(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    morning = datetime(2020, 1, 5, 6, 0, tzinfo=UTC)
    metric_id = await _samples(_WEIGHT, [(morning, 100.0, "kg", "apple")])
    await client.post(
        "/api/v1/measurements",
        json={
            "items": [
                {
                    "metric_key": "body.weight",
                    "date_key": "2020-01-05",
                    "value": 98,
                }
            ]
        },
        headers=auth,
    )
    await _reconcile()
    assert (await _daily(metric_id))[date(2020, 1, 5)].value_num == 98


async def test_alias_rows_merge_into_canonical_key(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    alias = MetricSpec(
        "sleep.spo2_avg", "SpO2 nuit", "sleep", "float", "%", "avg"
    )
    target = QUANTITY_SPECS["HKQuantityTypeIdentifierOxygenSaturation"]
    async with SessionFactory() as session:
        await MetricCache().id_for(session, alias)
        target_id = await MetricCache().id_for(session, target)
        await session.commit()
    await client.post(
        "/api/v1/measurements",
        json={
            "items": [
                {
                    "metric_key": "sleep.spo2_avg",
                    "date_key": "2026-06-03",
                    "value": 0.97,
                }
            ]
        },
        headers=auth,
    )
    report = await _reconcile()
    assert report["merged"] == {"sleep.spo2_avg": 1}
    row = (await _daily(target_id))[date(2026, 6, 3)]
    assert row.value_num == pytest.approx(97.0)


async def test_mapped_ingest_lands_on_canonical_key(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "date_key": "2026-06-04",
        "samples": [
            {
                "healthkit_type": "HKQuantityTypeIdentifierOxygenSaturation",
                "value": 0.96,
                "unit": "%",
            }
        ],
    }
    resp = await client.post("/api/v1/ingest/watch", json=body, headers=auth)
    assert resp.json()["recorded"] == 1
    listed = await client.get(
        "/api/v1/measurements", params={"metric_key": "body.spo2"}, headers=auth
    )
    assert listed.json()[0]["value"] == pytest.approx(96.0)


async def test_inventory_and_reconcile_endpoints(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    start = datetime(2026, 6, 5, 7, 0, tzinfo=UTC)
    await _samples(_WEIGHT, [(start, 90.0, "kg", "auto-export")])
    await _reconcile()
    resp = await client.get("/api/v1/data/inventory", headers=auth)
    assert resp.status_code == 200
    weight = next(r for r in resp.json() if r["key"] == "body.weight")
    assert weight["raw"][0]["source"] == "auto-export"
    assert weight["raw"][0]["first"] == "2026-06-05"
    assert weight["daily"][0]["count"] == 1
    queued = await client.post("/api/v1/data/reconcile", headers=auth)
    assert queued.status_code == 202
