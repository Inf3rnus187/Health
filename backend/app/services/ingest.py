"""Ingest generic samples (Watch/CPAP) into measurements (§7.1)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ingest import IngestPayload, IngestResult, IngestSample
from app.schemas.measurement import MeasurementIn
from app.services import canonical, mappings
from app.services import measurements as measure
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec, synth_spec
from app.services.apple_health.units import convert


async def ingest(
    session: AsyncSession,
    user_id: str,
    source: str,
    payload: IngestPayload,
    *,
    token_id: str | None = None,
) -> IngestResult:
    """Map samples to metrics and record them; report unresolved keys."""
    cache = MetricCache()
    items: list[MeasurementIn] = []
    skipped: list[str] = []
    for sample in payload.samples:
        target = await _resolve_key(session, user_id, source, sample, cache)
        if target is None:
            skipped.append(sample.healthkit_type or "unknown")
            continue
        items.append(_to_item(target, sample, payload.date_key))
    recorded = await _record(session, user_id, source, items, token_id)
    return IngestResult(recorded=recorded, skipped=skipped)


async def _resolve_key(
    session: AsyncSession,
    user_id: str,
    source: str,
    sample: IngestSample,
    cache: MetricCache,
) -> MetricSpec | str | None:
    """The sample's canonical metric (curated spec when known)."""
    key = sample.metric_key
    if not key and sample.healthkit_type:
        key = await mappings.resolve(
            session, user_id, source, sample.healthkit_type
        )
        if key is None:
            spec = synth_spec(sample.healthkit_type, sample.unit)
            await cache.id_for(session, spec)
            key = spec.key
    if not key:
        return None
    key = canonical.canonical(key)
    return await canonical.ensure(session, key, cache) or key


def _to_item(
    target: MetricSpec | str, sample: IngestSample, default_day: date
) -> MeasurementIn:
    """A measurement input, converted to the metric's unit when known."""
    day = sample.ts.date() if sample.ts else default_day
    value = sample.value
    if isinstance(target, MetricSpec) and isinstance(value, int | float):
        value = convert(float(value), sample.unit or "", target.unit)
    key = target.key if isinstance(target, MetricSpec) else target
    return MeasurementIn(
        metric_key=key, date_key=day, value=value, recorded_at=sample.ts
    )


async def _record(
    session: AsyncSession,
    user_id: str,
    source: str,
    items: list[MeasurementIn],
    token_id: str | None,
) -> int:
    """Persist the resolved items, returning the row count."""
    if not items:
        return 0
    rows = await measure.record_batch(
        session, user_id, items, source=source, token_id=token_id
    )
    return len(rows)
