"""Keep what a daily write replaces, so an overwrite can be undone.

``POST /measurements`` is idempotent: it *replaces* the value a metric
already holds for the day — the right rule for a re-sent sync, a loss
when someone meant to add. The values it replaces go to the audit log.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.measurement import MeasurementIn
from app.services.canonical import canonical

#: Replaced values logged per write (a large re-sync logs the first ones).
LIMIT = 200


async def replaced(
    session: AsyncSession, user_id: str, items: list[MeasurementIn]
) -> list[dict[str, Any]]:
    """The stored daily values that ``items`` are about to replace."""
    wanted = {
        (canonical(i.metric_key), i.date_key)
        for i in items
        if i.event_id is None
    }
    if not wanted:
        return []
    stmt = (
        select(MetricDefinition.key, Measurement)
        .join(MetricDefinition, MetricDefinition.id == Measurement.metric_id)
        .where(
            Measurement.user_id == user_id,
            Measurement.event_id.is_(None),
            MetricDefinition.key.in_({key for key, _ in wanted}),
            Measurement.date_key.in_({day for _, day in wanted}),
        )
    )
    rows = (await session.execute(stmt)).all()
    found = [
        _entry(key, row) for key, row in rows if (key, row.date_key) in wanted
    ]
    return found[:LIMIT]


def _entry(key: str, row: Measurement) -> dict[str, Any]:
    """One replaced value, JSON-ready."""
    return {
        "metric": key,
        "date": row.date_key.isoformat(),
        "previous": _value(row),
    }


def _value(row: Measurement) -> Any:
    """Whichever typed column holds the row's value."""
    for value in (row.value_num, row.value_bool, row.value_text):
        if value is not None:
            return value
    if row.value_time is not None:
        return row.value_time.isoformat()
    return row.value_json
