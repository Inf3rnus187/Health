"""Daily values recomputed from raw samples — one rule for every channel.

Apple Health reaches the hub through two channels carrying the SAME
HealthKit data: the native export (``apple``) and Health Auto Export
(``auto-export``). Adding both would double-count steps, while "last
writer wins" let a partial Health-Auto-Export day overwrite a full
native day. So a day's value is computed from the raw samples of ONE
HealthKit channel — the one holding the most samples that day — plus
every other source, in the metric's unit and with its aggregation.
A later manual / lab entry of an instant metric (e.g. a weigh-in typed
in the web form after the scale synced) is kept.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.models.user import User
from app.services.apple_health.units import convert
from app.services.daily_acc import HEALTHKIT, Acc, reduce_day

#: Sources that only ever wrote daily roll-ups of HealthKit samples.
_ROLLUP_SOURCES = HEALTHKIT | {"watch"}
_STREAM = 20000

Days = dict[date, dict[str, Acc]]


async def user_zone(session: AsyncSession, user_id: str) -> ZoneInfo:
    """The user's time zone (local days), UTC if unknown."""
    user = await session.get(User, user_id)
    try:
        return ZoneInfo(user.timezone if user else "UTC")
    except (KeyError, ValueError):
        return ZoneInfo("UTC")


async def rebuild(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    tz: ZoneInfo,
    since: date | None = None,
) -> int:
    """Recompute a metric's daily values from its samples; count days."""
    days = await _scan(session, user_id, metric, tz, since)
    if not days:
        return 0
    existing = await _existing(session, user_id, metric.id, min(days))
    for day, sources in days.items():
        value, source, at = reduce_day(sources, metric.aggregation_hint)
        row = existing.get(day)
        if row is not None and _keeps(row, metric, at):
            continue
        _write(session, user_id, metric, day, (value, source, at), row)
    await session.flush()
    return len(days)


async def _scan(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    tz: ZoneInfo,
    since: date | None,
) -> Days:
    """Stream the metric's numeric samples into per-day, per-source sums."""
    stmt = select(
        HealthSample.start_at,
        HealthSample.value_num,
        HealthSample.unit,
        HealthSample.source,
    ).where(
        HealthSample.user_id == user_id,
        HealthSample.metric_id == metric.id,
        HealthSample.value_num.is_not(None),
    )
    if since is not None:
        floor = datetime.combine(since, time.min, tzinfo=tz)
        stmt = stmt.where(HealthSample.start_at >= floor)
    days: Days = {}
    result = await session.stream(stmt.execution_options(yield_per=_STREAM))
    async for at, value, unit, source in result:
        local = (at if at.tzinfo else at.replace(tzinfo=UTC)).astimezone(tz)
        acc = days.setdefault(local.date(), {}).setdefault(source, Acc())
        acc.add(local, convert(float(value), unit or "", metric.unit))
    return days


async def _existing(
    session: AsyncSession, user_id: str, metric_id: str, first: date
) -> dict[date, Measurement]:
    """The metric's daily rows from ``first`` on, by day."""
    result = await session.execute(
        select(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
            Measurement.date_key >= first,
            Measurement.event_id.is_(None),
        )
    )
    return {row.date_key: row for row in result.scalars().all()}


def _keeps(row: Measurement, metric: MetricDefinition, at: datetime) -> bool:
    """Keep an explicit entry (manual, lab…) made after the day's samples.

    Cumulative metrics (steps…) are always recomputed: their samples are
    the complete day.
    """
    if row.source in _ROLLUP_SOURCES or metric.aggregation_hint == "sum":
        return False
    recorded = row.recorded_at
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=UTC)
    return recorded > at


def _write(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    day: date,
    result: tuple[float, str, datetime],
    row: Measurement | None,
) -> None:
    """Insert or update the day's single row."""
    value, source, at = result
    if row is None:
        row = Measurement(
            user_id=user_id, metric_id=metric.id, date_key=day, recorded_at=at
        )
        session.add(row)
    row.value_num = value
    row.value_text = None
    row.source = source
