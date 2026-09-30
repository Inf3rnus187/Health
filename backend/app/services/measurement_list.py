"""The daily values a user asks for, as JSON, fast on a whole history.

``GET /measurements`` without a filter returns every daily value of
every metric (44 000 on the test history). They are read as columns, not
ORM objects, and written by pydantic's own serializer straight from the
database's types, with ``value`` read by the schema's rule: the same
bytes as the schema gives, several times faster (docs/performance.md).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic_core import to_json
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.schemas.measurement import VALUE_COLUMNS, MeasurementOut, first_set
from app.services import metrics as metrics_service

#: The columns the answer holds (the schema's fields, in its order).
_NAMES = tuple(MeasurementOut.model_fields)
_COLUMNS = tuple(getattr(Measurement, name) for name in _NAMES)
_TYPED = slice(_NAMES.index(VALUE_COLUMNS[0]), None)
#: By day, then time, then id: the same order on every call.
ORDER = (Measurement.date_key, Measurement.recorded_at, Measurement.id)


async def conditions(
    session: AsyncSession,
    user_id: str,
    *,
    metric_key: str | None = None,
    start: date | None = None,
    end: date | None = None,
    event_id: str | None = None,
) -> list[ColumnElement[bool]]:
    """The user's values, narrowed by the filters given."""
    found = [Measurement.user_id == user_id]
    if metric_key is not None:
        metric = await metrics_service.get_metric(session, metric_key)
        found.append(Measurement.metric_id == metric.id)
    if start is not None:
        found.append(Measurement.date_key >= start)
    if end is not None:
        found.append(Measurement.date_key <= end)
    if event_id is not None:
        found.append(Measurement.event_id == event_id)
    return found


async def as_json(session: AsyncSession, user_id: str, **filters: Any) -> bytes:
    """The values as the JSON list of ``MeasurementOut``."""
    wanted = await conditions(session, user_id, **filters)
    stmt = select(*_COLUMNS).where(*wanted).order_by(*ORDER)
    rows = (await session.execute(stmt)).all()
    return to_json([_plain(row) for row in rows])


def _plain(row: Any) -> dict[str, Any]:
    """One row as ``MeasurementOut`` writes it (``value`` last)."""
    found = dict(zip(_NAMES, row, strict=True))
    found["value"] = first_set(row[_TYPED])
    return found
