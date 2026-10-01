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

from collections.abc import AsyncIterator, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.models.user import User
from app.services.apple_health.units import converter
from app.services.daily_acc import HEALTHKIT, Acc, reduce_day

#: Sources that only ever wrote daily roll-ups of HealthKit samples.
_ROLLUP_SOURCES = HEALTHKIT | {"watch"}
_STREAM = get_settings().rollup_read_block
_DAY = timedelta(days=1)

Days = dict[date, dict[str, Acc]]
#: Local days [first, stop) of a part of a metric; None: no bound.
Span = tuple[date | None, date | None]


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
    span: Span | None = None,
    in_table_order: bool = False,
) -> int:
    """Recompute a metric's daily values from its samples; count days.

    ``span``: only these local days, a part of the metric (the reconcile
    computes the parts of a large metric at the same time).
    ``in_table_order``: the samples read in the table's order, never the
    index's, whatever the size of the metric (the reconcile, whole or in
    parts: a day's samples always come in the same order).
    """
    bounds = (since, span, in_table_order)
    return len(await rebuild_days(session, user_id, metric, tz, bounds))


async def rebuild_days(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    tz: ZoneInfo,
    bounds: tuple[date | None, Span | None, bool] = (None, None, False),
) -> set[date]:
    """:func:`rebuild`, returning the days that have numeric samples.

    ``bounds``: ``(since, span, in_table_order)``. Each day returned now
    has its value; a day not returned has no numeric sample.
    """
    since, span, in_table_order = bounds
    ordered = in_table_order or span is not None
    days = await _scan(session, user_id, metric, tz, (since, span, ordered))
    if not days:
        return set()
    existing = await _existing(session, user_id, metric.id, min(days))
    for day, sources in days.items():
        value, source, at = reduce_day(sources, metric.aggregation_hint)
        row = existing.get(day)
        if row is not None and _keeps(row, metric, at):
            continue
        _write(session, user_id, metric, day, (value, source, at), row)
    await session.flush()
    return set(days)


async def _scan(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    tz: ZoneInfo,
    bounds: tuple[date | None, Span | None, bool],
) -> Days:
    """Stream the metric's numeric samples into per-day, per-source sums."""
    since, span, ordered = bounds
    stmt = _samples(user_id, metric, tz, since, span)
    days: Days = {}
    async for rows in _blocks(session, stmt, in_table_order=ordered):
        _fold(days, rows, tz, metric.unit)
    if span is None:
        return days
    first, stop = span  # the day more read on each side is dropped
    return {
        day: sources
        for day, sources in days.items()
        if (first is None or day >= first) and (stop is None or day < stop)
    }


def _samples(
    user_id: str,
    metric: MetricDefinition,
    tz: ZoneInfo,
    since: date | None,
    span: Span | None,
) -> Select[Any]:
    """The metric's numeric samples, from ``since``, around ``span``.

    Bounds in UTC: SQLite drops the zone of a bound time (local midnight
    would then be read as UTC midnight). Around a span, a day more on
    each side: every sample of its days is read, whatever the zone's
    offset or a change of time that day.
    """
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
    first, stop = span or (None, None)
    if since is not None:
        stmt = stmt.where(HealthSample.start_at >= _midnight(since, tz))
    if first is not None:
        stmt = stmt.where(HealthSample.start_at >= _midnight(first - _DAY, tz))
    if stop is not None:
        stmt = stmt.where(HealthSample.start_at < _midnight(stop + _DAY, tz))
    return stmt


def _midnight(day: date, tz: ZoneInfo) -> datetime:
    """The start of a local day, in UTC."""
    return datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)


async def _blocks(
    session: AsyncSession, stmt: Select[Any], in_table_order: bool = False
) -> AsyncIterator[Sequence[Any]]:
    """The statement's plain rows, a block at a time (not a row, nor all).

    PostgreSQL: read by asyncpg itself, with the very SQL SQLAlchemy
    compiles (same plan, same order of rows) but without its row objects,
    which took half the time of reading a million samples. The table is
    read from its start, not from where another read of it stopped: the
    samples always come in the same order, so a day's sum is the same to
    the last digit. ``in_table_order``: never in the index's order (a
    full or bitmap scan): a part of a metric and the whole metric give
    each day's samples in the same order, so the same values.
    """
    connection = await session.connection()
    if connection.dialect.name != "postgresql":
        if in_table_order:  # SQLite (tests): its rows' order, not an index's
            stmt = stmt.order_by(literal_column("rowid"))
        result = await connection.stream(
            stmt.execution_options(yield_per=_STREAM)
        )
        async for rows in result.partitions():
            yield rows
        return
    await connection.execute(text("SET LOCAL synchronize_seqscans = off"))
    if in_table_order:
        await connection.execute(text("SET LOCAL enable_indexscan = off"))
    compiled = stmt.compile(dialect=connection.dialect)
    params = [compiled.params[name] for name in compiled.positiontup or ()]
    raw = (await connection.get_raw_connection()).driver_connection
    if raw is None:  # never: a pooled asyncpg connection
        raise RuntimeError("no asyncpg connection")
    cursor = await raw.cursor(str(compiled), *params)  # in the transaction
    while rows := await cursor.fetch(_STREAM):
        yield rows
    if in_table_order:  # the rest of the transaction as the planner likes
        await connection.execute(text("SET LOCAL enable_indexscan TO DEFAULT"))


def _fold(
    days: Days, rows: Sequence[Any], tz: ZoneInfo, unit: str | None
) -> None:
    """Add a block of samples to their day's and source's accumulator."""
    for at, value, sample_unit, source in rows:
        local = (at if at.tzinfo else at.replace(tzinfo=UTC)).astimezone(tz)
        per_source = days.setdefault(local.date(), {})
        acc = per_source.get(source)
        if acc is None:
            acc = per_source[source] = Acc()
        acc.add(local, converter(sample_unit or "", unit)(float(value)))


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
