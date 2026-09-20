"""Headline metrics for the home page's daily recap."""

from __future__ import annotations

from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.services import metrics as metrics_service

#: The metrics shown as tiles, in order (missing ones are skipped).
HEADLINE_KEYS = (
    "body.weight",
    "activity.steps",
    "rest.hr",
    "heart.rate",
    "sleep.asleep",
    "body.spo2",
    "activity.active_energy",
    "activity.exercise_min",
)


class Tile(NamedTuple):
    """One headline metric's latest value."""

    key: str
    label: str
    unit: str | None
    value: float
    date_key: date
    at: datetime | None


async def headline(session: AsyncSession, user_id: str) -> list[Tile]:
    """Return the latest value of each available headline metric."""
    tiles: list[Tile] = []
    for key in HEADLINE_KEYS:
        tile = await _tile(session, user_id, key)
        if tile is not None:
            tiles.append(tile)
    return tiles


async def _tile(session: AsyncSession, user_id: str, key: str) -> Tile | None:
    """Build one tile from a metric's most recent numeric value."""
    try:
        metric = await metrics_service.get_metric(session, key)
    except NotFoundError:
        return None
    row = await _latest(session, user_id, metric.id)
    if row is None or row.value_num is None:
        return None
    at = await _latest_time(session, user_id, metric.id, row.recorded_at)
    return Tile(key, metric.label, metric.unit, row.value_num, row.date_key, at)


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


async def _latest_time(
    session: AsyncSession,
    user_id: str,
    metric_id: str,
    fallback: datetime | None,
) -> datetime | None:
    """Return the newest raw sample time for a metric (else fallback)."""
    result = await session.execute(
        select(HealthSample.start_at)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
        )
        .order_by(HealthSample.start_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none() or fallback
