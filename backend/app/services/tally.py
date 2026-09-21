"""Increment a daily counter metric (café, cigarette, bouteille d'eau).

The daily fact table keeps one row per metric/day, so a plain ingest
*replaces* the day's value — wrong for a one-tap counter. ``increment``
reads the current day total, adds the amount and upserts the sum, so each
Shortcut tap adds to the running total for the day.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.measurement import MeasurementIn
from app.services import measurement_values as values
from app.services import measurements as measure
from app.services import metrics as metrics_service


async def increment(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    amount: float,
    day: date,
    *,
    token_id: str | None = None,
) -> float:
    """Add ``amount`` to a metric's daily total; return the new total."""
    metric = await metrics_service.get_metric(session, metric_key)
    total = await _current(session, user_id, metric_key, day) + amount
    values.validate(metric, total)
    item = MeasurementIn(metric_key=metric_key, date_key=day, value=total)
    await measure.record_batch(
        session, user_id, [item], source="watch", token_id=token_id
    )
    return total


async def _current(
    session: AsyncSession, user_id: str, metric_key: str, day: date
) -> float:
    """Return the metric's stored value for the day, or 0."""
    rows = await measure.query(
        session, user_id, metric_key=metric_key, start=day, end=day
    )
    for row in rows:
        if row.value_num is not None:
            return row.value_num
    return 0.0
