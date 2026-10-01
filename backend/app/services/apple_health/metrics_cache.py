"""Resolve (and create on demand) the metric id for a spec.

Imports touch a bounded set of distinct metrics, so a per-key lookup on
first use — creating the row when absent — keeps the dynamic registry in
sync without a migration.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import MetricDefinition
from app.services.apple_health.spec import MetricSpec


class MetricCache:
    """Cache metric ids by key, creating missing metrics as needed."""

    def __init__(self) -> None:
        """Start with an empty id cache."""
        self._ids: dict[str, str] = {}

    async def preload(
        self, session: AsyncSession, specs: Iterable[MetricSpec]
    ) -> None:
        """Resolve these specs' ids in one query (the missing ones made)."""
        wanted = {spec.key: spec for spec in specs if spec.key not in self._ids}
        if not wanted:
            return
        found = await session.execute(
            select(MetricDefinition.key, MetricDefinition.id).where(
                MetricDefinition.key.in_(list(wanted))
            )
        )
        self._ids.update({key: metric_id for key, metric_id in found.all()})
        for key, spec in wanted.items():
            if key not in self._ids:
                await self.id_for(session, spec)  # a new metric, made

    async def id_for(self, session: AsyncSession, spec: MetricSpec) -> str:
        """Return the metric id for a spec, creating the metric if new."""
        cached = self._ids.get(spec.key)
        if cached is not None:
            return cached
        metric_id = await _resolve(session, spec)
        self._ids[spec.key] = metric_id
        return metric_id


async def _resolve(session: AsyncSession, spec: MetricSpec) -> str:
    """Find the metric by key or create it, returning its id."""
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.key == spec.key)
    )
    metric = result.scalar_one_or_none()
    if metric is None:
        metric = _build(spec)
        session.add(metric)
        await session.flush()
    return metric.id


def _build(spec: MetricSpec) -> MetricDefinition:
    """Build a metric-definition row from a spec."""
    return MetricDefinition(
        key=spec.key,
        label=spec.label,
        domain=spec.domain,
        data_type=spec.data_type,
        unit=spec.unit,
        source="watch",
        aggregation_hint=spec.agg,
    )
