"""Idempotent recording and querying of measurement facts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.base import utcnow
from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.measurement import MeasurementIn
from app.services import measurement_values as values
from app.services import metrics as metrics_service
from app.services.aggregation import rolling


async def record_batch(
    session: AsyncSession,
    user_id: str,
    items: list[MeasurementIn],
    *,
    source: str,
    token_id: str | None = None,
    event_id: str | None = None,
) -> list[Measurement]:
    """Upsert a batch of measurements (no duplicates, §7.3)."""
    catalog = await _load_metrics(session, {i.metric_key for i in items})
    rows: list[Measurement] = []
    for item in items:
        metric = _resolve(catalog, item.metric_key)
        values.validate(metric, item.value)
        eid = event_id if event_id is not None else item.event_id
        rows.append(
            await _upsert(session, user_id, metric, item, source, token_id, eid)
        )
    await session.flush()
    return rows


async def query(
    session: AsyncSession,
    user_id: str,
    *,
    metric_key: str | None = None,
    start: date | None = None,
    end: date | None = None,
    event_id: str | None = None,
) -> list[Measurement]:
    """Return raw measurements matching the given filters."""
    stmt = select(Measurement).where(Measurement.user_id == user_id)
    if metric_key is not None:
        metric = await metrics_service.get_metric(session, metric_key)
        stmt = stmt.where(Measurement.metric_id == metric.id)
    if start is not None:
        stmt = stmt.where(Measurement.date_key >= start)
    if end is not None:
        stmt = stmt.where(Measurement.date_key <= end)
    if event_id is not None:
        stmt = stmt.where(Measurement.event_id == event_id)
    stmt = stmt.order_by(Measurement.date_key, Measurement.recorded_at)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def aggregate(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    agg: str,
    window_days: int,
) -> list[tuple[date, float]]:
    """Return a rolling-aggregated series for a numeric metric."""
    rows = await query(session, user_id, metric_key=metric_key)
    points = [
        (r.date_key, r.value_num) for r in rows if r.value_num is not None
    ]
    return rolling(points, window_days, agg)


async def delete_one(
    session: AsyncSession, user_id: str, measurement_id: str
) -> None:
    """Delete one of the user's measurements or raise NotFound."""
    row = await session.get(Measurement, measurement_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Measurement not found")
    await session.delete(row)
    await session.flush()


async def delete_many(
    session: AsyncSession, user_id: str, ids: list[str]
) -> int:
    """Delete several of the user's measurements; return the count."""
    result = await session.execute(
        sql_delete(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.id.in_(ids),
        )
    )
    await session.flush()
    return cast("CursorResult[Any]", result).rowcount or 0


def _resolve(
    catalog: dict[str, MetricDefinition], key: str
) -> MetricDefinition:
    """Return an active, writable metric from the preloaded catalog."""
    metric = catalog.get(key)
    if metric is None:
        raise NotFoundError(f"Unknown metric: {key}")
    if not metric.is_active:
        raise InvalidInputError(f"Inactive metric: {key}")
    if metric.source == "derived":
        raise InvalidInputError(f"Derived metric is read-only: {key}")
    return metric


async def _load_metrics(
    session: AsyncSession, keys: set[str]
) -> dict[str, MetricDefinition]:
    """Preload the metrics referenced by a batch in one query."""
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.key.in_(keys))
    )
    return {m.key: m for m in result.scalars().all()}


async def _upsert(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    item: MeasurementIn,
    source: str,
    token_id: str | None,
    event_id: str | None,
) -> Measurement:
    """Insert or update the unique row for this metric/day/event."""
    columns = values.columns_for(metric, item.value)
    recorded = item.recorded_at or utcnow()
    row_source = item.source or source
    existing = await _find(session, user_id, metric.id, item.date_key, event_id)
    if existing is None:
        row = _build(user_id, metric.id, item.date_key, event_id, recorded)
        _apply(row, row_source, token_id, columns)
        session.add(row)
        return row
    _apply(existing, row_source, token_id, columns)
    return existing


def _build(
    user_id: str,
    metric_id: str,
    date_key: date,
    event_id: str | None,
    recorded: datetime,
) -> Measurement:
    """Create a bare measurement row (values applied separately)."""
    return Measurement(
        user_id=user_id,
        metric_id=metric_id,
        date_key=date_key,
        event_id=event_id,
        recorded_at=recorded,
    )


def _apply(
    row: Measurement,
    source: str,
    token_id: str | None,
    columns: dict[str, object],
) -> None:
    """Set the typed value columns and provenance on ``row``."""
    row.value_num = None
    row.value_bool = None
    row.value_text = None
    row.value_time = None
    row.value_json = None
    for name, value in columns.items():
        setattr(row, name, value)
    row.source = source
    row.token_id = token_id


async def _find(
    session: AsyncSession,
    user_id: str,
    metric_id: str,
    date_key: date,
    event_id: str | None,
) -> Measurement | None:
    """Return the existing unique row for this key tuple, if any."""
    stmt = select(Measurement).where(
        Measurement.user_id == user_id,
        Measurement.metric_id == metric_id,
        Measurement.date_key == date_key,
    )
    if event_id is None:
        stmt = stmt.where(Measurement.event_id.is_(None))
    else:
        stmt = stmt.where(Measurement.event_id == event_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
