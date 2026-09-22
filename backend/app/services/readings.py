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

#: Daily rows written by syncs (not an explicit entry).
SYNCED = frozenset({"apple", "auto-export", "watch"})


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
        return _entry(day_value, daily)
    value, at, unit, source = sample
    if metric.aggregation_hint == "sum" or value is None:
        return Reading(day_value, at, daily.source)
    explicit = daily.source not in SYNCED
    if explicit and measured_at(daily) > _aware(at):
        return _entry(day_value, daily)
    return Reading(convert(value, unit or "", metric.unit), at, source)


def _entry(value: float, daily: Measurement) -> Reading:
    """A reading from a daily row, dated by its measurement day."""
    timed = _aware(daily.recorded_at).date() == daily.date_key
    return Reading(value, measured_at(daily), daily.source, timed)


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
