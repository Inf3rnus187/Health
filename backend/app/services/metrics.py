"""CRUD for the dynamic metric registry (no migration on change)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.metric import MetricDefinition
from app.schemas.metric import MetricCreate, MetricUpdate
from app.services import metric_memo
from app.services.canonical import canonical


async def list_metrics(
    session: AsyncSession,
    *,
    domain: str | None = None,
    source: str | None = None,
    active: bool | None = None,
) -> list[MetricDefinition]:
    """Return metric definitions matching the given filters."""
    stmt = select(MetricDefinition)
    if domain is not None:
        stmt = stmt.where(MetricDefinition.domain == domain)
    if source is not None:
        stmt = stmt.where(MetricDefinition.source == source)
    if active is not None:
        stmt = stmt.where(MetricDefinition.is_active == active)
    result = await session.execute(stmt.order_by(MetricDefinition.key))
    return list(result.scalars().all())


async def get_metric(session: AsyncSession, key: str) -> MetricDefinition:
    """Return one metric by key (aliases resolve to their canonical).

    Kept for the session once read (:mod:`metric_memo`).
    """
    wanted = canonical(key)
    seen = metric_memo.seen(session)
    kept: MetricDefinition | None = seen.get(wanted)
    if kept is not None:
        return kept
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.key == wanted)
    )
    metric = result.scalar_one_or_none()
    if metric is None:
        raise NotFoundError(f"Unknown metric: {key}")
    seen[wanted] = metric
    return metric


async def prefetch(
    session: AsyncSession, keys: list[str]
) -> dict[str, MetricDefinition]:
    """Several metrics by key in one query (unknown keys left out).

    Kept for the session like :func:`get_metric`'s.
    """
    seen = metric_memo.seen(session)
    wanted = {key: canonical(key) for key in keys}
    missing = {c for c in wanted.values() if c not in seen}
    if missing:
        result = await session.execute(
            select(MetricDefinition).where(MetricDefinition.key.in_(missing))
        )
        seen.update({metric.key: metric for metric in result.scalars()})
    return {key: seen[c] for key, c in wanted.items() if c in seen}


async def create_metric(
    session: AsyncSession, created_by: str | None, data: MetricCreate
) -> MetricDefinition:
    """Register a new metric, rejecting a duplicate key."""
    if await _exists(session, data.key):
        raise ConflictError(f"Metric already exists: {data.key}")
    metric = MetricDefinition(created_by=created_by, **data.model_dump())
    session.add(metric)
    await session.flush()
    return metric


async def update_metric(
    session: AsyncSession, key: str, data: MetricUpdate
) -> MetricDefinition:
    """Apply a partial update to an existing metric."""
    metric = await get_metric(session, key)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(metric, field, value)
    await session.flush()
    return metric


async def _exists(session: AsyncSession, key: str) -> bool:
    """Return whether a metric with ``key`` already exists."""
    result = await session.execute(
        select(MetricDefinition.id).where(MetricDefinition.key == key)
    )
    return result.scalar_one_or_none() is not None
