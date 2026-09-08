"""Ingest generic samples (Watch/CPAP) into measurements (§7.1)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ingest import IngestPayload, IngestResult, IngestSample
from app.schemas.measurement import MeasurementIn
from app.services import mappings
from app.services import measurements as measure


async def ingest(
    session: AsyncSession,
    user_id: str,
    source: str,
    payload: IngestPayload,
    *,
    token_id: str | None = None,
) -> IngestResult:
    """Map samples to metrics and record them; report unresolved keys."""
    items: list[MeasurementIn] = []
    skipped: list[str] = []
    for sample in payload.samples:
        key = await _resolve_key(session, user_id, source, sample)
        if key is None:
            skipped.append(sample.healthkit_type or "unknown")
            continue
        items.append(_to_item(key, sample, payload.date_key))
    recorded = await _record(session, user_id, source, items, token_id)
    return IngestResult(recorded=recorded, skipped=skipped)


async def _resolve_key(
    session: AsyncSession,
    user_id: str,
    source: str,
    sample: IngestSample,
) -> str | None:
    """Return the metric key for a sample (direct or via mapping)."""
    if sample.metric_key:
        return sample.metric_key
    if sample.healthkit_type:
        return await mappings.resolve(
            session, user_id, source, sample.healthkit_type
        )
    return None


def _to_item(
    key: str, sample: IngestSample, default_day: date
) -> MeasurementIn:
    """Build a measurement input from a resolved sample."""
    day = sample.ts.date() if sample.ts else default_day
    return MeasurementIn(
        metric_key=key,
        date_key=day,
        value=sample.value,
        recorded_at=sample.ts,
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
