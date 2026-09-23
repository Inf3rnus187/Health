"""Nights typed by hand when the watch did not record (flat battery…).

A typed night is a raw sleep sample from the source ``manual`` (bedtime
→ wake-up, awakenings in its value) and sets that day's ``sleep.asleep``
so charts and reports see it. Only typed nights can be deleted here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.base import new_uuid
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementIn
from app.services import measurements, metrics, timed_entries
from app.services.apple_health.spec import SLEEP_RAW
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc

DEVICE = "Saisie manuelle"
_MAX_HOURS = 20


async def add(
    session: AsyncSession,
    user_id: str,
    bedtime: datetime,
    wake_time: datetime,
    awakenings: int | None,
) -> dict[str, Any]:
    """Record a night typed by hand (times without offset: local)."""
    tz = await user_zone(session, user_id)
    start, end = (
        t if t.tzinfo else t.replace(tzinfo=tz) for t in (bedtime, wake_time)
    )
    minutes = (end - start).total_seconds() / 60
    if not 0 < minutes <= _MAX_HOURS * 60:
        raise InvalidInputError(
            "Le lever doit suivre le coucher (20 h au plus)."
        )
    metric = await timed_entries.metric_for(session, SLEEP_RAW)
    row = HealthSample(
        id=new_uuid(), user_id=user_id, metric_id=metric.id,
        start_at=utc(start), end_at=utc(end), value_text="asleep",
        value_num=awakenings, source="manual", device=DEVICE,
    )  # fmt: skip
    session.add(row)
    day = end.astimezone(tz).date()
    item = MeasurementIn(
        metric_key="sleep.asleep", date_key=day, value=round(minutes)
    )
    await measurements.record_batch(session, user_id, [item], source="manual")
    return {"id": row.id, "wake_day": day, "asleep_min": round(minutes)}


async def remove(session: AsyncSession, user_id: str, sample_id: str) -> None:
    """Delete a typed night and the daily value it set."""
    row = await session.get(HealthSample, sample_id)
    if row is None or row.user_id != user_id or row.source != "manual":
        raise NotFoundError("Typed night not found")
    tz = await user_zone(session, user_id)
    day = utc(row.end_at or row.start_at).astimezone(tz).date()
    metric = await metrics.get_metric(session, "sleep.asleep")
    await session.delete(row)
    await session.execute(
        sql_delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric.id,
            Measurement.date_key == day,
            Measurement.source == "manual",
        )
    )


async def typed(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    """The nights typed by hand, newest first (to check or delete)."""
    metric = await timed_entries.metric_for(session, SLEEP_RAW)
    rows = await session.execute(
        select(HealthSample)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric.id,
            HealthSample.source == "manual",
        )
        .order_by(HealthSample.start_at.desc())
    )
    return [
        {
            "id": r.id,
            "bedtime": utc(r.start_at),
            "wake_time": utc(r.end_at or r.start_at),
            "awakenings": r.value_num,
        }
        for r in rows.scalars()
    ]
