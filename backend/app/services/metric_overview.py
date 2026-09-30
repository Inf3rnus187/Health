"""One metric at a glance — the same numbers on every page.

Latest reading (see :mod:`readings`), the last day's value (total,
average… per the metric's aggregation), 7 / 30-day averages, 30-day
range, the sources of the daily values and the daily series. Home,
dashboards, Santé, Données, the reports and the MCP server all use it.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Any

from sqlalchemy import and_, func, or_, select, tuple_
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
    return (await _views(session, user_id, {key: metric}, days))[key]


async def overviews(
    session: AsyncSession, user_id: str, keys: list[str], days: int = 365
) -> dict[str, dict[str, Any]]:
    """Several metrics read together (the home page's tiles).

    A handful of queries for all of them, not a set per metric. Unknown
    keys are left out.
    """
    found = await metrics_service.prefetch(session, keys)
    return await _views(session, user_id, found, days)


async def _views(
    session: AsyncSession,
    user_id: str,
    metrics: dict[str, MetricDefinition],
    days: int,
) -> dict[str, dict[str, Any]]:
    """Each metric's view, from rows read for all of them at once."""
    ids = list({metric.id for metric in metrics.values()})
    newest = await _newest(session, user_id, ids)
    lasts = {mid: row.date_key for mid, row in newest.items()}
    rows = await _since(session, user_id, lasts, max(days, 30))
    history = await _history(session, user_id, list(lasts))
    out = {}
    for key, metric in metrics.items():
        found = (newest.get(metric.id), rows.get(metric.id, []), history)
        out[key] = await _view(session, user_id, metric, found, days)
    return out


async def _view(
    session: AsyncSession,
    user_id: str,
    metric: MetricDefinition,
    found: tuple[Measurement | None, list[Row], dict[str, Any]],
    days: int,
) -> dict[str, Any]:
    """One metric's view from its newest row, its window and its history."""
    newest, rows, history = found
    out = _head(metric)
    if newest is None or not rows:
        return out
    last = newest.date_key
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
        **history[metric.id],
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


def _numeric(user_id: str) -> list[Any]:
    """The user's numeric daily values."""
    return [Measurement.user_id == user_id, Measurement.value_num.is_not(None)]


async def _newest(
    session: AsyncSession, user_id: str, ids: list[str]
) -> dict[str, Measurement]:
    """Each metric's newest numeric daily row (the day shown, the reading).

    The rows of each metric's last day, in one query; then that day's
    latest entry.
    """
    last_days = (
        select(Measurement.metric_id, func.max(Measurement.date_key))
        .where(*_numeric(user_id), Measurement.metric_id.in_(ids))
        .group_by(Measurement.metric_id)
    )
    rows = await session.execute(
        select(Measurement).where(
            *_numeric(user_id),
            tuple_(Measurement.metric_id, Measurement.date_key).in_(last_days),
        )
    )
    out: dict[str, Measurement] = {}
    for row in rows.scalars():
        best = out.get(row.metric_id)
        rank = (row.recorded_at, row.id)
        if best is None or rank > (best.recorded_at, best.id):
            out[row.metric_id] = row
    return out


async def _since(
    session: AsyncSession, user_id: str, lasts: dict[str, date], days: int
) -> dict[str, list[Row]]:
    """Each metric's daily values of its last ``days`` days, oldest first.

    Only the window a page shows is read, not years of values: the
    counts over all time come from :func:`_history`.
    """
    if not lasts:
        return {}
    windows = [
        and_(
            Measurement.metric_id == mid,
            Measurement.date_key > last - timedelta(days=days),
        )
        for mid, last in lasts.items()
    ]
    result = await session.execute(
        select(
            Measurement.metric_id, Measurement.date_key, Measurement.value_num
        )
        .where(*_numeric(user_id), or_(*windows))
        .order_by(Measurement.date_key, Measurement.recorded_at, Measurement.id)
    )
    out: dict[str, list[Row]] = defaultdict(list)
    for mid, day, value in result.all():
        out[mid].append((day, float(value)))
    return out


async def _history(
    session: AsyncSession, user_id: str, ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Days counted, first day and sources over all time, by the database."""
    result = await session.execute(
        select(
            Measurement.metric_id,
            Measurement.source,
            func.count(),
            func.min(Measurement.date_key),
        )
        .where(*_numeric(user_id), Measurement.metric_id.in_(ids))
        .group_by(Measurement.metric_id, Measurement.source)
    )
    per_metric: dict[str, list[Any]] = defaultdict(list)
    for mid, *row in result.all():
        per_metric[mid].append(row)
    return {mid: _counted(found) for mid, found in per_metric.items()}


def _counted(found: list[Any]) -> dict[str, Any]:
    """One metric's day count, first day and sources (most days first)."""
    found = sorted(found, key=lambda row: (-row[1], row[2], row[0]))
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
