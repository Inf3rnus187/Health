"""Bring already-stored data in line with the HealthKit catalog.

Run by the reconcile job:
* metric definitions created before the catalog get their French label,
  Health-app domain and daily aggregation (units only when unset);
* category events imported before (symptoms, notifications, stand
  hours, mindfulness…) get their numeric value, so they chart and sum;
* Health Auto Export percentages (already 0-100) are tagged so they are
  never scaled a second time.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.services.apple_health import hk_catalog
from app.services.apple_health.hk_values import category_value
from app.services.apple_health.spec import synth_spec
from app.services.apple_health.units import PERCENT_0_100

_BATCH = 5000


def _by_key() -> dict[str, tuple[str, hk_catalog.HkType]]:
    """Metric key → (HealthKit identifier, catalog entry)."""
    return {
        synth_spec(hk, None).key: (hk, spec)
        for hk, spec in hk_catalog.TYPES.items()
    }


async def sync_definitions(session: AsyncSession) -> int:
    """Label / domain / aggregation of catalog metrics; count updated."""
    known = _by_key()
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.key.in_(known))
    )
    changed = 0
    for metric in result.scalars().all():
        spec = known[metric.key][1]
        before = (metric.label, metric.domain, metric.aggregation_hint)
        metric.label, metric.domain = spec.label, spec.domain
        metric.aggregation_hint = spec.agg
        metric.unit = metric.unit or spec.unit
        changed += before != (spec.label, spec.domain, spec.agg)
    await session.flush()
    return changed


async def backfill_categories(session: AsyncSession, user_id: str) -> int:
    """Give imported category events their numeric value; count them."""
    known = _by_key()
    result = await session.execute(
        select(MetricDefinition.id, MetricDefinition.key).where(
            MetricDefinition.key.in_(known)
        )
    )
    filled = 0
    for metric_id, key in result.all():
        hk_type, spec = known[key]
        if spec.family:
            filled += await _fill(session, user_id, metric_id, hk_type)
    return filled


async def tag_percentages(session: AsyncSession, user_id: str) -> int:
    """Mark Health Auto Export percentages as already on a 0-100 scale."""
    result = await session.execute(
        update(HealthSample)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.source == "auto-export",
            HealthSample.unit == "%",
        )
        .values(unit=PERCENT_0_100)
    )
    return cast("CursorResult[Any]", result).rowcount or 0


async def _fill(
    session: AsyncSession, user_id: str, metric_id: str, hk_type: str
) -> int:
    """Compute value_num for one category metric's events."""
    if hk_catalog.TYPES[hk_type].family == "duration":
        return await _fill_durations(session, user_id, metric_id, hk_type)
    texts = await session.execute(
        select(HealthSample.value_text)
        .where(*_pending(user_id, metric_id))
        .distinct()
    )
    count = 0
    for text in texts.scalars().all():
        value = category_value(hk_type, text, None, None)
        if value is None:
            continue
        done = await session.execute(
            update(HealthSample)
            .where(*_pending(user_id, metric_id))
            .where(_same_text(text))
            .values(value_num=value)
        )
        count += cast("CursorResult[Any]", done).rowcount or 0
    return count


async def _fill_durations(
    session: AsyncSession, user_id: str, metric_id: str, hk_type: str
) -> int:
    """Minutes of each session (few rows: mindfulness)."""
    rows = await session.execute(
        select(HealthSample.id, HealthSample.start_at, HealthSample.end_at)
        .where(*_pending(user_id, metric_id))
        .limit(_BATCH)
    )
    count = 0
    for sample_id, start, end in rows.all():
        value = category_value(hk_type, None, start, end)
        if value is not None:
            await session.execute(
                update(HealthSample)
                .where(HealthSample.id == sample_id)
                .values(value_num=value)
            )
            count += 1
    return count


def _pending(user_id: str, metric_id: str) -> tuple[Any, ...]:
    """Filter: this user's events of a metric without a numeric value."""
    return (
        HealthSample.user_id == user_id,
        HealthSample.metric_id == metric_id,
        HealthSample.value_num.is_(None),
    )


def _same_text(text: str | None) -> Any:
    """Filter on the raw category value (NULL-safe)."""
    if text is None:
        return HealthSample.value_text.is_(None)
    return HealthSample.value_text == text
