"""Headline metrics for the home page's health-hub recap.

Each tile carries the latest value, the time of the last raw reading, and
lightweight evolution stats (day-over-day delta, 7-day average, and a short
daily sparkline) so the home page reads like a dashboard, not a list.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import metrics as metrics_service
from app.services.apple_health.units import convert

#: The metrics shown as tiles, in order (missing ones are skipped).
HEADLINE_KEYS = (
    "body.weight",
    "activity.steps",
    "rest.hr",
    "heart.rate",
    "heart.hrv",
    "sleep.asleep",
    "body.spo2",
    "body.resp_rate",
    "activity.active_energy",
    "activity.exercise_min",
    "habit.cigarettes",
    "habit.coffee",
)

#: The stored bottle counter and the litres it represents (1 bottle = 1.5 L).
_WATER_KEY = "water.bottles_1_5"
_LITERS_PER_BOTTLE = 1.5


class Tile(NamedTuple):
    """One headline metric's latest value plus evolution stats."""

    key: str
    label: str
    unit: str | None
    value: float
    date_key: date
    at: datetime | None
    delta: float | None
    avg7: float | None
    spark: list[float]


async def headline(session: AsyncSession, user_id: str) -> list[Tile]:
    """Return the latest value + stats of each available headline metric."""
    tiles: list[Tile] = []
    for key in HEADLINE_KEYS:
        tile = await _tile(session, user_id, key)
        if tile is not None:
            tiles.append(tile)
    water = await _water_tile(session, user_id)
    if water is not None:
        tiles.append(water)
    return tiles


async def _water_tile(session: AsyncSession, user_id: str) -> Tile | None:
    """Litres d'eau (1.5 L per finished bottle) from the stored counter."""
    try:
        metric = await metrics_service.get_metric(session, _WATER_KEY)
    except NotFoundError:
        return None
    row = await _latest(session, user_id, metric.id)
    if row is None or row.value_num is None:
        return None
    raw = await _series(session, user_id, metric.id)
    series = [value * _LITERS_PER_BOTTLE for value in raw]
    return Tile(
        key="hydration.liters",
        label="Eau",
        unit="L",
        value=round(row.value_num * _LITERS_PER_BOTTLE, 2),
        date_key=row.date_key,
        at=None,
        delta=_delta(series),
        avg7=_avg7(series),
        spark=_spark(series),
    )


async def _tile(session: AsyncSession, user_id: str, key: str) -> Tile | None:
    """Build one tile from a metric's recent daily roll-ups."""
    try:
        metric = await metrics_service.get_metric(session, key)
    except NotFoundError:
        return None
    row = await _latest(session, user_id, metric.id)
    if row is None or row.value_num is None:
        return None
    series = await _series(session, user_id, metric.id)
    value, at = await _headline(session, user_id, metric, row)
    return Tile(
        key=key,
        label=metric.label,
        unit=metric.unit,
        value=value,
        date_key=row.date_key,
        at=at,
        delta=_delta(series),
        avg7=_avg7(series),
        spark=_spark(series),
    )


async def _headline(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    rollup: Measurement,
) -> tuple[float, datetime | None]:
    """Latest reading for instant metrics; daily total for cumulative ones.

    The raw reading is converted to the metric's unit (lb → kg, SpO2
    fraction → %), and an explicit entry newer than the last synced
    sample (a weigh-in typed in the web form) wins.
    """
    latest = await _latest_sample(session, user_id, metric.id)
    daily = float(rollup.value_num or 0.0)
    if latest is None:
        return daily, rollup.recorded_at
    value, at, unit = latest
    if metric.aggregation_hint == "sum" or value is None:
        return daily, at
    explicit = rollup.source not in _SYNCED
    if explicit and _aware(rollup.recorded_at) > _aware(at):
        return daily, rollup.recorded_at
    return convert(value, unit or "", metric.unit), at


async def _latest(
    session: AsyncSession, user_id: str, metric_id: str
) -> Measurement | None:
    """Return the most recent measurement for a metric."""
    result = await session.execute(
        select(Measurement)
        .where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
        )
        .order_by(Measurement.date_key.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _series(
    session: AsyncSession, user_id: str, metric_id: str
) -> list[float]:
    """Return up to 30 recent daily values, oldest first."""
    result = await session.execute(
        select(Measurement.value_num)
        .where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
            Measurement.value_num.is_not(None),
        )
        .order_by(Measurement.date_key.desc())
        .limit(30)
    )
    values = [float(v) for (v,) in result.all()]
    values.reverse()
    return values


async def _latest_sample(
    session: AsyncSession, user_id: str, metric_id: str
) -> tuple[float | None, datetime, str | None] | None:
    """The newest raw sample's (value, time, unit) for a metric, or None."""
    result = await session.execute(
        select(HealthSample.value_num, HealthSample.start_at, HealthSample.unit)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
        )
        .order_by(HealthSample.start_at.desc())
        .limit(1)
    )
    row = result.first()
    return (row[0], row[1], row[2]) if row is not None else None


def _aware(at: datetime) -> datetime:
    """Treat a naive timestamp (SQLite) as UTC."""
    return at if at.tzinfo else at.replace(tzinfo=UTC)


_MIN_POINTS = 2
#: Daily rows written by syncs (not an explicit entry).
_SYNCED = ("apple", "auto-export", "watch")


def _delta(series: list[float]) -> float | None:
    """Change between the two most recent daily values."""
    if len(series) < _MIN_POINTS:
        return None
    return round(series[-1] - series[-2], 2)


def _avg7(series: list[float]) -> float | None:
    """Mean of the last seven daily values."""
    window = series[-7:]
    if not window:
        return None
    return round(sum(window) / len(window), 2)


def _spark(series: list[float]) -> list[float]:
    """The last 14 daily values, for a sparkline."""
    return [round(value, 2) for value in series[-14:]]
