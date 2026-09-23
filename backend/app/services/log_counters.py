"""Write imported counts: daily counters and timed pee entries.

Never destructive: a counter day already holding a value keeps the
larger of the two; a pee time already stored is not added twice.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementIn
from app.services import measurements, metrics, timed_entries, urination


async def counts(
    session: AsyncSession,
    user_id: str,
    key: str,
    per_day: dict[date, int],
    dry_run: bool,
) -> dict[str, Any]:
    """Fill the counter's days: empty → set, smaller → raised, else kept."""
    stored = await _stored(session, user_id, key, set(per_day))
    items, outcome = [], {"set": 0, "raised": 0, "kept": 0}
    for day, count in sorted(per_day.items()):
        old = stored.get(day)
        state = "set" if old is None else "raised" if old < count else "kept"
        outcome[state] += 1
        if state != "kept":
            items.append(
                MeasurementIn(metric_key=key, date_key=day, value=count)
            )
    if items and not dry_run:
        await measurements.record_batch(
            session, user_id, items, source="import"
        )
    return {"days": len(per_day), "events": sum(per_day.values()), **outcome}


async def pee(
    session: AsyncSession,
    user_id: str,
    stamps: list[datetime],
    dry_run: bool,
) -> dict[str, Any]:
    """One timed pee per stamp; a time already stored (± 1 min) is kept."""
    metric = await timed_entries.metric_for(session, urination.SPEC)
    added = existing = 0
    for at in sorted(set(stamps)):
        found = await session.execute(
            select(HealthSample.id).where(
                HealthSample.user_id == user_id,
                HealthSample.metric_id == metric.id,
                HealthSample.start_at.between(
                    at - timedelta(minutes=1), at + timedelta(minutes=1)
                ),
            )
        )
        if found.first() is not None:
            existing += 1
            continue
        added += 1
        if not dry_run:
            await urination.log(session, user_id, at)
    return {"events": len(stamps), "added": added, "existing": existing}


async def _stored(
    session: AsyncSession, user_id: str, key: str, days: set[date]
) -> dict[date, float]:
    """The counter's stored daily values on ``days``."""
    metric = await metrics.get_metric(session, key)
    rows = await session.execute(
        select(Measurement.date_key, Measurement.value_num).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric.id,
            Measurement.date_key.in_(days),
            Measurement.event_id.is_(None),
        )
    )
    return {day: value or 0.0 for day, value in rows.all()}
