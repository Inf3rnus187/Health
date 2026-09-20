"""Paginated, filtered browsing of raw health samples."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.health_raw import HealthSample
from app.services import metrics as metrics_service
from app.services.apple_health.import_runner import reset


async def page(
    session: AsyncSession,
    user_id: str,
    *,
    metric_key: str | None,
    start: date | None,
    end: date | None,
    limit: int,
    offset: int,
) -> tuple[list[HealthSample], int]:
    """Return a page of samples and the total number that match."""
    base = select(HealthSample).where(HealthSample.user_id == user_id)
    stmt = await _filter(session, base, metric_key, start, end)
    if stmt is None:
        return [], 0
    total = await _count(session, stmt)
    result = await session.execute(
        stmt.order_by(HealthSample.start_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def wipe_imported(session: AsyncSession, user_id: str) -> None:
    """Delete every Apple-imported sample, workout, ECG and route."""
    await reset(session, user_id)


async def _filter(
    session: AsyncSession,
    stmt: Select[tuple[HealthSample]],
    metric_key: str | None,
    start: date | None,
    end: date | None,
) -> Select[tuple[HealthSample]] | None:
    """Apply metric and date filters; None if the metric is unknown."""
    if metric_key:
        try:
            metric = await metrics_service.get_metric(session, metric_key)
        except NotFoundError:
            return None
        stmt = stmt.where(HealthSample.metric_id == metric.id)
    if start is not None:
        stmt = stmt.where(HealthSample.start_at >= _floor(start))
    if end is not None:
        stmt = stmt.where(HealthSample.start_at < _floor(end + timedelta(1)))
    return stmt


async def _count(
    session: AsyncSession, stmt: Select[tuple[HealthSample]]
) -> int:
    """Count the rows a filtered statement would return."""
    counter = select(func.count()).select_from(stmt.subquery())
    return int((await session.execute(counter)).scalar_one())


def _floor(day: date) -> datetime:
    """Return midnight UTC for a calendar day."""
    return datetime.combine(day, time.min, tzinfo=UTC)
