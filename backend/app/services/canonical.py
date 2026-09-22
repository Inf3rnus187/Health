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
from app.services.apple_health.spec import (
    QUANTITY_SPECS,
    MetricSpec,
    synth_spec,
)
from app.services.apple_health.units import convert
from app.services.hae_names import HAE_MAP

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


def _hae_legacy() -> dict[str, str]:
    """Keys created from Health Auto Export names before they were mapped.

    An unmapped name (e.g. ``walking_running_distance``) used to become
    ``apple.<name>``; it now resolves to the HealthKit type's metric.
    """
    out: dict[str, str] = {}
    for name, hk_type in HAE_MAP.items():
        legacy = f"apple.{name}"
        target = synth_spec(hk_type, None).key
        if legacy != target:
            out[legacy] = target
    return out


ALIASES.update(_hae_legacy())


def canonical(key: str) -> str:
    """The canonical key for ``key`` (itself when already canonical)."""
    return ALIASES.get(key, key)


async def merge(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Move this user's alias rows onto canonical metrics; count moves.

    A missing canonical metric is created from its spec (never by renaming
    the alias: several aliases can share one target, and definitions are
    shared by every user). Alias definitions left empty are dropped.
    """
    moved: dict[str, int] = {}
    cache = MetricCache()
    for alias, target in ALIASES.items():
        count = await _merge_one(session, user_id, alias, target, cache)
        if count:
            moved[alias] = count
    await session.flush()
    return moved


async def _merge_one(
    session: AsyncSession,
    user_id: str,
    alias: str,
    target: str,
    cache: MetricCache,
) -> int:
    """Fold one alias metric into its target; count the moved rows."""
    found = await _found(session, alias, target)
    source = found.get(alias)
    if source is None:
        return 0
    if target not in found:
        if not await _used(session, source.id, user_id):
            return 0
        await cache.id_for(session, _spec_for(target, source))
        found = await _found(session, alias, target)
    count = await _move(session, user_id, source, found[target])
    if not await _used(session, source.id, None):
        await session.delete(source)
    return count


async def _found(
    session: AsyncSession, alias: str, target: str
) -> dict[str, MetricDefinition]:
    """The alias and target metric definitions that exist, by key."""
    result = await session.execute(
        select(MetricDefinition).where(
            MetricDefinition.key.in_([alias, target])
        )
    )
    return {m.key: m for m in result.scalars().all()}


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


async def _used(
    session: AsyncSession, metric_id: str, user_id: str | None
) -> bool:
    """Whether a metric still holds rows (for one user, or anyone)."""
    for model in (HealthSample, Measurement):
        query = select(model.id).where(model.metric_id == metric_id)
        if user_id is not None:
            query = query.where(model.user_id == user_id)
        if (await session.execute(query.limit(1))).first() is not None:
            return True
    return False


def _target_specs() -> dict[str, MetricSpec]:
    """Canonical key → spec, for creating a missing canonical metric."""
    specs = {spec.key: spec for spec in QUANTITY_SPECS.values()}
    for hk_type in HAE_MAP.values():
        spec = synth_spec(hk_type, None)
        specs.setdefault(spec.key, spec)
    return specs


_SPECS = _target_specs()


def _spec_for(target: str, alias: MetricDefinition) -> MetricSpec:
    """The spec of a canonical key (else modelled on the alias metric)."""
    known = _SPECS.get(target)
    if known is not None:
        return known
    return MetricSpec(
        target,
        alias.label,
        target.split(".", 1)[0],
        alias.data_type,
        alias.unit,
        alias.aggregation_hint or "avg",
    )


async def ensure(
    session: AsyncSession, key: str, cache: MetricCache
) -> MetricSpec | None:
    """Create a canonical metric from its known spec if it is missing."""
    spec = _SPECS.get(key)
    if spec is not None:
        await cache.id_for(session, spec)
    return spec
