"""The latest reading of a metric — one definition for every page.

* cumulative metrics (steps, energy…): the last day's total;
* instant metrics (heart rate, weight…): the newest raw sample, in the
  metric's unit (lb → kg, SpO2 fraction → %), unless an explicit entry
  (typed weigh-in, lab value…) is newer.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services.apple_health.units import convert
from app.services.daily_rollup import user_zone

#: Daily rows written by syncs (not an explicit entry).
SYNCED = frozenset({"apple", "auto-export", "healthkit", "watch"})


class Reading(NamedTuple):
    """A value with when and where it was measured."""

    value: float
    at: datetime | None
    source: str
    #: False when only the day is known (a lab value, a dated entry).
    timed: bool = True


async def latest(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    daily: Measurement,
) -> Reading:
    """The metric's latest reading given its newest daily row."""
    day_value = float(daily.value_num or 0.0)
    sample = await _newest_sample(session, user_id, metric.id)
    if sample is None:
        return await _entry(session, user_id, day_value, daily)
    value, at, unit, source = sample
    if metric.aggregation_hint == "sum" or value is None:
        return Reading(day_value, at, daily.source)
    explicit = daily.source not in SYNCED
    if explicit and measured_at(daily) > _aware(at):
        return await _entry(session, user_id, day_value, daily)
    return Reading(convert(value, unit or "", metric.unit), at, source)


async def _entry(
    session: AsyncSession, user_id: str, value: float, daily: Measurement
) -> Reading:
    """A reading from a daily row, dated by its measurement day.

    Timed when entered on its own day in the user's time zone (a coffee
    added at 01:30 in Paris is 23:30 UTC the day before): a counter keeps
    the time of its last addition (:mod:`tally`).
    """
    at = _aware(daily.recorded_at)
    zone = await user_zone(session, user_id)
    if at.astimezone(zone).date() == daily.date_key:
        return Reading(value, at, daily.source)
    return Reading(value, measured_at(daily), daily.source, timed=False)


def measured_at(daily: Measurement) -> datetime:
    """When a daily value was measured, not when it was entered.

    A lab result imported today for last week's blood test is dated by
    its day; an entry typed on its own day keeps its time.
    """
    at = _aware(daily.recorded_at)
    if at.date() == daily.date_key:
        return at
    return datetime.combine(daily.date_key, time(12), tzinfo=UTC)


async def _newest_sample(
    session: AsyncSession, user_id: str, metric_id: str
) -> tuple[float | None, datetime, str | None, str] | None:
    """The newest raw sample's value, time, unit and source."""
    result = await session.execute(
        select(
            HealthSample.value_num,
            HealthSample.start_at,
            HealthSample.unit,
            HealthSample.source,
        )
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
        )
        .order_by(HealthSample.start_at.desc())
        .limit(1)
    )
    row = result.first()
    return (row[0], row[1], row[2], row[3]) if row is not None else None


def _aware(at: datetime) -> datetime:
    """Treat a naive timestamp (SQLite) as UTC."""
    return at if at.tzinfo else at.replace(tzinfo=UTC)
