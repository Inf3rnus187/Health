"""Dashboard schemas: per-domain series ready to plot (§10)."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.measurement import SeriesPoint


class DashboardSeries(BaseModel):
    """One plottable series (rolling-aggregated) for a metric."""

    metric_key: str
    label: str
    unit: str | None
    agg: str
    window_days: int
    points: list[SeriesPoint]


class DashboardOut(BaseModel):
    """All numeric series for one domain."""

    domain: str
    window_days: int
    series: list[DashboardSeries]
