"""Pee log: one tap = one timed entry; the daily value is the count.

Apple Health has no urination type (only a bladder-incontinence
symptom), so the hub keeps its own ``elimination.urination`` metric,
fed like any other: timed raw samples + one daily value.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.services import daily_rollup, timed_entries
from app.services.apple_health.spec import MetricSpec

SPEC = MetricSpec(
    "elimination.urination",
    "Mictions (pipi)",
    "elimination",
    "int",
    "count",
    "sum",
)
_SOURCE = "manual"
_DEVICE = "journal"


async def log(
    session: AsyncSession, user_id: str, at: datetime | None
) -> dict[str, Any]:
    """Record one urination (now by default); return it with the day."""
    metric = await timed_entries.metric_for(session, SPEC)
    sample = HealthSample(
        id=new_uuid(),
        user_id=user_id,
        metric_id=metric.id,
        start_at=timed_entries.utc(at or utcnow()),
        value_num=1.0,
        unit="count",
        source=_SOURCE,
        device=_DEVICE,
    )
    session.add(sample)
    day = await timed_entries.local_day(session, user_id, sample.start_at)
    await timed_entries.refresh(session, user_id, metric, {day})
    return {"id": sample.id, "at": sample.start_at.isoformat(), "day": day}


async def day_list(
    session: AsyncSession, user_id: str, day: date
) -> list[dict[str, Any]]:
    """The day's urinations (id and time), in order."""
    metric = await timed_entries.metric_for(session, SPEC)
    tz = await daily_rollup.user_zone(session, user_id)
    start, end = timed_entries.day_bounds(day, tz)
    rows = await session.execute(
        select(HealthSample.id, HealthSample.start_at)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric.id,
            HealthSample.start_at >= start,
            HealthSample.start_at < end,
        )
        .order_by(HealthSample.start_at)
    )
    return [
        {"id": i, "at": timed_entries.utc(at).isoformat()}
        for i, at in rows.all()
    ]


async def remove(session: AsyncSession, user_id: str, sample_id: str) -> None:
    """Delete one journal urination (not an imported sample)."""
    metric = await timed_entries.metric_for(session, SPEC)
    sample = await session.get(HealthSample, sample_id)
    if (
        sample is None
        or sample.user_id != user_id
        or sample.metric_id != metric.id
    ):
        raise NotFoundError("Urination not found")
    day = await timed_entries.local_day(session, user_id, sample.start_at)
    await session.delete(sample)
    await timed_entries.refresh(session, user_id, metric, {day})
