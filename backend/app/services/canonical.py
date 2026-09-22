"""One metric key per health concept, whatever the channel.

Older mappings and synthesized Apple keys stored the same concept under
several keys (SpO2 as ``sleep.spo2_avg`` and ``body.spo2``, waist as
``apple.waist_circumference`` and ``body.waist``…), so pages reading
different keys showed different things. Every write path resolves keys
through :func:`canonical`, and :func:`merge` moves a user's existing
alias rows onto the canonical metric (converting units).
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import QUANTITY_SPECS, MetricSpec
from app.services.apple_health.units import convert

#: Legacy / alternative key → canonical key.
ALIASES: dict[str, str] = {
    "sleep.spo2_avg": "body.spo2",
    "sleep.resp_rate": "body.resp_rate",
    "sleep.hrv": "heart.hrv",
    "stairs.floors": "activity.flights",
    "walk.distance": "activity.distance",
    "apple.waist_circumference": "body.waist",
    "apple.body_weight": "body.weight",
    "apple.body_mass": "body.weight",
    "apple.blood_glucose": "bio.glycemie",
}


def canonical(key: str) -> str:
    """The canonical key for ``key`` (itself when already canonical)."""
    return ALIASES.get(key, key)


async def merge(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Move this user's alias rows onto canonical metrics; count moves."""
    moved: dict[str, int] = {}
    for alias, target in ALIASES.items():
        pair = await _pair(session, alias, target)
        if pair is None:
            continue
        count = await _move(session, user_id, *pair)
        if count:
            moved[alias] = count
    await session.flush()
    return moved


async def _pair(
    session: AsyncSession, alias: str, target: str
) -> tuple[MetricDefinition, MetricDefinition] | None:
    """The alias metric and its target, when both exist."""
    result = await session.execute(
        select(MetricDefinition).where(
            MetricDefinition.key.in_([alias, target])
        )
    )
    found = {m.key: m for m in result.scalars().all()}
    if alias not in found or target not in found:
        return None
    return found[alias], found[target]


async def _move(
    session: AsyncSession,
    user_id: str,
    alias: MetricDefinition,
    target: MetricDefinition,
) -> int:
    """Re-point raw samples, then fold daily rows (target wins a day)."""
    samples = await session.execute(
        update(HealthSample)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == alias.id,
        )
        .values(metric_id=target.id)
    )
    folded = await _fold_daily(session, user_id, alias, target)
    return (cast("CursorResult[Any]", samples).rowcount or 0) + folded


async def _fold_daily(
    session: AsyncSession,
    user_id: str,
    alias: MetricDefinition,
    target: MetricDefinition,
) -> int:
    """Move alias daily rows to days the target lacks; drop the rest."""
    taken = await _days(session, user_id, target.id)
    rows = await session.execute(
        select(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == alias.id,
            Measurement.event_id.is_(None),
        )
    )
    free = [r for r in rows.scalars().all() if r.date_key not in taken]
    for row in free:
        _repoint(row, alias, target)
    await session.flush()
    await session.execute(
        delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == alias.id,
            Measurement.event_id.is_(None),
        )
    )
    return len(free)


def _repoint(
    row: Measurement, alias: MetricDefinition, target: MetricDefinition
) -> None:
    """Attach a daily row to the target metric, in the target's unit."""
    row.metric_id = target.id
    if row.value_num is not None:
        row.value_num = convert(row.value_num, alias.unit or "", target.unit)


async def _days(
    session: AsyncSession, user_id: str, metric_id: str
) -> set[date]:
    """Days on which the user already has a daily value for a metric."""
    result = await session.execute(
        select(Measurement.date_key).where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
        )
    )
    return set(result.scalars().all())


async def ensure(
    session: AsyncSession, key: str, cache: MetricCache
) -> MetricSpec | None:
    """Create a canonical metric from its curated spec if it is missing."""
    spec = next((s for s in QUANTITY_SPECS.values() if s.key == key), None)
    if spec is not None:
        await cache.id_for(session, spec)
    return spec
