"""Assemble per-domain dashboards with rolling series (§10)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import NUMERIC_TYPES
from app.models.metric import MetricDefinition
from app.schemas.dashboard import DashboardOut, DashboardSeries
from app.schemas.measurement import SeriesPoint
from app.services import measurements as measure
from app.services import metrics as metrics_service


async def get_dashboard(
    session: AsyncSession, user_id: str, domain: str, window: int
) -> DashboardOut:
    """Return every numeric metric of a domain as a rolling series."""
    metrics = await metrics_service.list_metrics(
        session, domain=domain, active=True
    )
    numeric = [m for m in metrics if m.data_type in NUMERIC_TYPES]
    series = [
        await _series(session, user_id, metric, window) for metric in numeric
    ]
    return DashboardOut(domain=domain, window_days=window, series=series)


async def _series(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    window: int,
) -> DashboardSeries:
    """Build one rolling series for a metric using its agg hint."""
    points = await measure.aggregate(
        session, user_id, metric.key, metric.aggregation_hint, window
    )
    return DashboardSeries(
        metric_key=metric.key,
        label=metric.label,
        unit=metric.unit,
        agg=metric.aggregation_hint,
        window_days=window,
        points=[SeriesPoint(date_key=d, value=v) for d, v in points],
    )
