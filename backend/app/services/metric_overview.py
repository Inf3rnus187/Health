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

from sqlalchemy import func, select
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

Row = tuple[date, float]


async def overview(
    session: AsyncSession, user_id: str, key: str, days: int = 365
) -> dict[str, Any]:
    """Everything a page shows about one metric."""
    metric = await metrics_service.get_metric(session, key)
    out = _head(metric)
    newest = await _newest(session, user_id, metric.id)
    if newest is None:
        return out
    last = newest.date_key
    rows = await _since(session, user_id, metric.id, last, max(days, 30))
    reading = await readings.latest(session, user_id, metric, newest)
    out.update(
        latest={
            "value": round(reading.value, 2),
            "at": reading.at.isoformat() if reading.at else None,
            "source": reading.source,
            "timed": reading.timed,
        },
        day={"date": last.isoformat(), "value": rows[-1][1]},
        **_stats(rows, last),
        **await _history(session, user_id, metric.id),
        series=[
            {"date": d.isoformat(), "value": round(v, 2)}
            for d, v in rows
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


def _numeric(user_id: str, metric_id: str) -> list[Any]:
    """The user's numeric daily values of one metric."""
    return [
        Measurement.user_id == user_id,
        Measurement.metric_id == metric_id,
        Measurement.value_num.is_not(None),
    ]


async def _newest(
    session: AsyncSession, user_id: str, metric_id: str
) -> Measurement | None:
    """The newest numeric daily row (the day shown, the latest reading)."""
    result = await session.execute(
        select(Measurement)
        .where(*_numeric(user_id, metric_id))
        .order_by(Measurement.date_key.desc(), Measurement.recorded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _since(
    session: AsyncSession, user_id: str, metric_id: str, last: date, days: int
) -> list[Row]:
    """The daily values of the last ``days`` days, oldest first.

    Only the window a page shows is read, not years of values: the
    counts over all time come from :func:`_history`.
    """
    result = await session.execute(
        select(Measurement.date_key, Measurement.value_num)
        .where(
            *_numeric(user_id, metric_id),
            Measurement.date_key > last - timedelta(days=days),
        )
        .order_by(Measurement.date_key, Measurement.recorded_at)
    )
    return [(day, float(value)) for day, value in result.all()]


async def _history(
    session: AsyncSession, user_id: str, metric_id: str
) -> dict[str, Any]:
    """Days counted, first day and sources over all time, by the database."""
    result = await session.execute(
        select(
            Measurement.source,
            func.count(),
            func.min(Measurement.date_key),
        )
        .where(*_numeric(user_id, metric_id))
        .group_by(Measurement.source)
    )
    found = sorted(result.all(), key=lambda row: (-row[1], row[2], row[0]))
    return {
        "days_count": sum(int(row[1]) for row in found),
        "first_day": min(row[2] for row in found).isoformat(),
        "sources": [{"source": row[0], "count": int(row[1])} for row in found],
    }


def _stats(rows: list[Row], last: date) -> dict[str, Any]:
    """7 / 30-day averages and the 30-day range."""
    week = [v for d, v in rows if d > last - timedelta(days=7)]
    month = [v for d, v in rows if d > last - timedelta(days=30)]
    return {
        "avg7": round(fmean(week), 2) if week else None,
        "avg30": round(fmean(month), 2) if month else None,
        "min30": round(min(month), 2) if month else None,
        "max30": round(max(month), 2) if month else None,
    }
