"""Everything stored for a user, per metric and per source.

One table answering "what do I have, where did it come from, which
period does it cover": raw samples and daily values, by source, with
their first / last dates — so nothing stays invisible. The raw samples'
counts are kept by the database (a few ms instead of counting millions
of rows, docs/performance.md).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import sample_counts

Row = dict[str, Any]


async def inventory(session: AsyncSession, user_id: str) -> list[Row]:
    """One row per metric the user has data for, grouped by source."""
    raw = await _raw(session, user_id)
    daily = await _daily(session, user_id)
    metrics = await _metrics(session, set(raw) | set(daily))
    rows = [
        {
            "key": metric.key,
            "label": metric.label,
            "domain": metric.domain,
            "unit": metric.unit,
            "raw": raw.get(metric.id, []),
            "daily": daily.get(metric.id, []),
        }
        for metric in metrics
    ]
    return sorted(rows, key=lambda row: (row["domain"], row["key"]))


async def _raw(session: AsyncSession, user_id: str) -> dict[str, list[Row]]:
    """Raw samples per metric and source: count and period.

    Read from the counts the database keeps exact at each write
    (:mod:`app.models.sample_counts`), not by counting every sample.
    """
    return _group(await sample_counts.of_user(session, user_id))


async def _daily(session: AsyncSession, user_id: str) -> dict[str, list[Row]]:
    """Daily values per metric and source: count and period."""
    result = await session.execute(
        select(
            Measurement.metric_id,
            Measurement.source,
            func.count(),
            func.min(Measurement.date_key),
            func.max(Measurement.date_key),
        )
        .where(Measurement.user_id == user_id)
        .group_by(Measurement.metric_id, Measurement.source)
    )
    return _group(result.all())


def _group(rows: Any) -> dict[str, list[Row]]:
    """``metric_id → [{source, count, first, last}]``."""
    out: dict[str, list[Row]] = {}
    for metric_id, source, count, first, last in rows:
        out.setdefault(metric_id, []).append(
            {
                "source": source,
                "count": int(count),
                "first": _day(first),
                "last": _day(last),
            }
        )
    return out


async def _metrics(
    session: AsyncSession, ids: set[str]
) -> list[MetricDefinition]:
    """The metric definitions for the given ids."""
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.id.in_(ids))
    )
    return list(result.scalars().all())


def _day(value: Any) -> str | None:
    """ISO day of a date / datetime (None stays None)."""
    if value is None:
        return None
    return str(value.isoformat())[:10]
