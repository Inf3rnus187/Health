"""Bucket a metric's daily values by day, week, month or year.

Aggregates the cached daily roll-ups (``measurements``) into calendar
buckets using the metric's own aggregation, so the dashboards can offer a
day/week/month/year view over the whole history.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.services import measurements as measure
from app.services import metrics as metrics_service

BUCKETS = frozenset({"day", "week", "month", "year"})


async def trend(
    session: AsyncSession, user_id: str, metric_key: str, bucket: str
) -> list[tuple[date, float]]:
    """Return ``(bucket start, value)`` points for a metric."""
    metric = await metrics_service.get_metric(session, metric_key)
    rows = await measure.query(session, user_id, metric_key=metric_key)
    grouped = _group(rows, bucket)
    agg = metric.aggregation_hint
    ordered = sorted(grouped.items())
    return [(day, _reduce(values, agg)) for day, values in ordered]


def _group(rows: list[Measurement], bucket: str) -> dict[date, list[float]]:
    """Collect numeric daily values into calendar buckets."""
    grouped: dict[date, list[float]] = {}
    for row in rows:
        if row.value_num is None:
            continue
        grouped.setdefault(_key(row.date_key, bucket), []).append(row.value_num)
    return grouped


def _key(day: date, bucket: str) -> date:
    """Return the canonical start date of a day's bucket."""
    if bucket == "week":
        return day - timedelta(days=day.weekday())
    if bucket == "month":
        return day.replace(day=1)
    if bucket == "year":
        return day.replace(month=1, day=1)
    return day


def _reduce(values: list[float], agg: str) -> float:
    """Combine a bucket's values using the metric's aggregation."""
    if agg == "sum":
        return sum(values)
    if agg == "min":
        return min(values)
    if agg == "max":
        return max(values)
    if agg == "last":
        return values[-1]
    return sum(values) / len(values)
