"""Build tidy measurement rows for export (§11).

Tidy shape: one row per measurement — ``date, metric_key, value, unit,
source`` — for easy reuse in spreadsheets, R/Python or another AI.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition


def _value(measurement: Measurement) -> Any:
    """Return the single stored value, formatting times as ISO text."""
    columns = (
        measurement.value_num,
        measurement.value_bool,
        measurement.value_text,
        measurement.value_time,
        measurement.value_json,
    )
    for candidate in columns:
        if candidate is None:
            continue
        return (
            candidate.isoformat()
            if hasattr(candidate, "isoformat")
            else candidate
        )
    return None


def _row(measurement: Measurement, metric: MetricDefinition) -> dict[str, Any]:
    """Build one tidy export row."""
    return {
        "date": measurement.date_key.isoformat(),
        "metric_key": metric.key,
        "value": _value(measurement),
        "unit": metric.unit,
        "source": measurement.source,
    }


async def tidy_rows(
    session: AsyncSession,
    user_id: str,
    *,
    domain: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Return tidy rows for a user, filtered by domain/period."""
    stmt = (
        select(Measurement, MetricDefinition)
        .join(
            MetricDefinition,
            Measurement.metric_id == MetricDefinition.id,
        )
        .where(Measurement.user_id == user_id)
    )
    if domain is not None:
        stmt = stmt.where(MetricDefinition.domain == domain)
    if start is not None:
        stmt = stmt.where(Measurement.date_key >= start)
    if end is not None:
        stmt = stmt.where(Measurement.date_key <= end)
    stmt = stmt.order_by(Measurement.date_key, MetricDefinition.key)
    result = await session.execute(stmt)
    return [_row(m, meta) for m, meta in result.all()]
