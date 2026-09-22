"""One metric at a glance — the same numbers on every page.

Latest reading (see :mod:`readings`), the last day's value (total,
average… per the metric's aggregation), 7 / 30-day averages, 30-day
range, the sources of the daily values and the daily series. Home,
dashboards, Santé, Données, the reports and the MCP server all use it.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import fmean
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import metrics as metrics_service
from app.services import readings

DAY_LABEL = {
    "sum": "Total du jour",
    "avg": "Moyenne du jour",
    "last": "Dernière valeur du jour",
    "min": "Minimum du jour",
    "max": "Maximum du jour",
}

Row = tuple[date, float, str]


async def overview(
    session: AsyncSession, user_id: str, key: str, days: int = 365
) -> dict[str, Any]:
    """Everything a page shows about one metric."""
    metric = await metrics_service.get_metric(session, key)
    newest, rows = await _daily(session, user_id, metric.id)
    out = _head(metric)
    if newest is None or not rows:
        return out
    reading = await readings.latest(session, user_id, metric, newest)
    last = rows[-1][0]
    out.update(
        latest={
            "value": round(reading.value, 2),
            "at": reading.at.isoformat() if reading.at else None,
            "source": reading.source,
        },
        day={"date": last.isoformat(), "value": rows[-1][1]},
        **_stats(rows, last),
        series=[
            {"date": d.isoformat(), "value": round(v, 2)}
            for d, v, _ in rows
            if d > last - timedelta(days=days)
        ],
    )
    return out


def _head(metric: MetricDefinition) -> dict[str, Any]:
    """Identity of the metric (always present)."""
    return {
        "key": metric.key,
        "label": metric.label,
        "unit": metric.unit,
        "domain": metric.domain,
        "aggregation": metric.aggregation_hint,
        "day_label": DAY_LABEL.get(metric.aggregation_hint, "Valeur du jour"),
        "latest": None,
        "day": None,
        "series": [],
    }


async def _daily(
    session: AsyncSession, user_id: str, metric_id: str
) -> tuple[Measurement | None, list[Row]]:
    """The newest daily row and every numeric daily value, oldest first."""
    result = await session.execute(
        select(Measurement)
        .where(
            Measurement.user_id == user_id,
            Measurement.metric_id == metric_id,
            Measurement.value_num.is_not(None),
        )
        .order_by(Measurement.date_key)
    )
    measured = list(result.scalars().all())
    rows = [(m.date_key, float(m.value_num or 0.0), m.source) for m in measured]
    return (measured[-1] if measured else None), rows


def _stats(rows: list[Row], last: date) -> dict[str, Any]:
    """Averages, range, coverage and sources."""
    week = [v for d, v, _ in rows if d > last - timedelta(days=7)]
    month = [v for d, v, _ in rows if d > last - timedelta(days=30)]
    sources: dict[str, int] = {}
    for _, _, source in rows:
        sources[source] = sources.get(source, 0) + 1
    return {
        "avg7": round(fmean(week), 2) if week else None,
        "avg30": round(fmean(month), 2) if month else None,
        "min30": round(min(month), 2) if month else None,
        "max30": round(max(month), 2) if month else None,
        "days_count": len(rows),
        "first_day": rows[0][0].isoformat(),
        "sources": [
            {"source": s, "count": n}
            for s, n in sorted(sources.items(), key=lambda kv: -kv[1])
        ],
    }
