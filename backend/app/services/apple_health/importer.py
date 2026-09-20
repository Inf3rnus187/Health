"""Import an Apple Health export into the measurement store.

Ensures the target metrics exist, folds the export's samples into daily
values, and upserts them in batches. Re-running is safe: each day's row
is overwritten with the same aggregated value (§7.3).
"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import MetricDefinition
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services.apple_health.accumulator import DailyAggregator
from app.services.apple_health.parser import parse
from app.services.apple_health.spec import (
    METRIC_DEFS,
    SEEDED_KEYS,
    MetricDef,
)

_BATCH = 500


class ImportSummary(NamedTuple):
    """Outcome of one import run."""

    metrics_added: int
    rows: int


async def run_import(
    session: AsyncSession, user_id: str, path: str
) -> ImportSummary:
    """Ensure metrics, aggregate the export and upsert daily rows."""
    added = await _ensure_metrics(session)
    aggregator = _aggregate(path)
    rows = await _record_all(session, user_id, aggregator)
    return ImportSummary(metrics_added=added, rows=rows)


def _aggregate(path: str) -> DailyAggregator:
    """Stream the export into one value per metric key and day."""
    aggregator = DailyAggregator()
    for sample in parse(path):
        aggregator.add(sample.metric_key, sample.day, sample.value)
    return aggregator


async def _ensure_metrics(session: AsyncSession) -> int:
    """Create any target metric that is not already registered."""
    result = await session.execute(select(MetricDefinition.key))
    existing = {row[0] for row in result.all()}
    added = 0
    for spec in METRIC_DEFS:
        if spec.key in existing or spec.key in SEEDED_KEYS:
            continue
        session.add(_metric_row(spec))
        added += 1
    await session.commit()
    return added


def _metric_row(spec: MetricDef) -> MetricDefinition:
    """Build a metric-definition row from a spec entry."""
    return MetricDefinition(
        key=spec.key,
        label=spec.label,
        domain=spec.domain,
        data_type=spec.data_type,
        unit=spec.unit,
        source="watch",
        aggregation_hint=spec.agg,
    )


async def _record_all(
    session: AsyncSession, user_id: str, aggregator: DailyAggregator
) -> int:
    """Upsert every aggregated bucket in bounded batches."""
    batch: list[MeasurementIn] = []
    total = 0
    for key, day, value in aggregator.results():
        batch.append(MeasurementIn(metric_key=key, date_key=day, value=value))
        if len(batch) >= _BATCH:
            total += await _flush(session, user_id, batch)
            batch = []
    total += await _flush(session, user_id, batch)
    return total


async def _flush(
    session: AsyncSession, user_id: str, batch: list[MeasurementIn]
) -> int:
    """Persist and commit one batch, returning its row count."""
    if not batch:
        return 0
    rows = await measure.record_batch(session, user_id, batch, source="watch")
    await session.commit()
    return len(rows)
