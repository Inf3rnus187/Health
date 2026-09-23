"""Timed journal entries stored as raw samples (pee, meal nutrients).

Like Apple samples, each entry keeps its exact time and the daily value
is rebuilt from the samples with the one daily rule
(:mod:`daily_rollup`), so the journal feeds the same metrics, charts and
reports as every other source. A day left without samples loses its
daily value (a deleted entry must not leave a stale total behind).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import daily_rollup
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec


async def metric_for(
    session: AsyncSession, spec: MetricSpec
) -> MetricDefinition:
    """The metric of a spec (created on first use)."""
    metric_id = await MetricCache().id_for(session, spec)
    metric = await session.get(MetricDefinition, metric_id)
    if metric is None:  # just created by the cache: cannot happen
        raise NotFoundError(f"Unknown metric: {spec.key}")
    return metric


def utc(at: datetime) -> datetime:
    """An instant in UTC (a naive value read back from SQLite is UTC)."""
    return at.replace(tzinfo=UTC) if at.tzinfo is None else at.astimezone(UTC)


def day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """A local day as a UTC [start, end) interval."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    return utc(start), utc(start + timedelta(days=1))


async def local_day(session: AsyncSession, user_id: str, at: datetime) -> date:
    """The user's local day of an instant."""
    tz = await daily_rollup.user_zone(session, user_id)
    return utc(at).astimezone(tz).date()


async def refresh(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    days: set[date],
) -> None:
    """Rebuild the daily values of ``days``; clear days left empty."""
    if not days:
        return
    await session.flush()
    tz = await daily_rollup.user_zone(session, user_id)
    await daily_rollup.rebuild(session, user_id, metric, tz, since=min(days))
    for day in days:
        start, end = day_bounds(day, tz)
        found = await session.execute(
            select(HealthSample.id)
            .where(
                HealthSample.user_id == user_id,
                HealthSample.metric_id == metric.id,
                HealthSample.start_at >= start,
                HealthSample.start_at < end,
            )
            .limit(1)
        )
        if found.first() is None:
            await _clear(session, user_id, metric.id, day)


async def _clear(
    session: AsyncSession, user_id: str, metric_id: str, day: date
) -> None:
    """Delete a day's daily value (no sample left behind it)."""
    await session.execute(
        delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
            Measurement.date_key == day,
            Measurement.event_id.is_(None),
        )
    )
