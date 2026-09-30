"""Make every page agree: one key per concept, daily values from raw data.

Run after each Apple import (and on demand from the web page):
0. stored data is aligned with the HealthKit catalog (French labels,
   domains, numeric category events, Health Auto Export percentages);
1. alias metrics are merged into their canonical metric (units
   converted), so e.g. SpO2 no longer lives under two keys;
2. every metric with raw samples gets its daily values recomputed with
   the single rule of :mod:`daily_rollup` — this also repairs days an
   interrupted import never wrote (e.g. weight present in the raw data
   but missing from the charts).

Also after each update of the hub, once per user (:mod:`reconcile_update`).
The log line ``reconciled`` gives the time it took (``seconds``) and the
slowest metrics (``slowest``), to see where it goes on real data.
"""

from __future__ import annotations

import time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.models.user import User
from app.services import canonical, catalog_sync, daily_rollup, sample_counts

_log = get_logger("reconcile")
#: The slowest metrics named in the log line.
_SLOWEST = 5


async def run(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Merge aliases, then rebuild every sampled metric; report counts."""
    started = time.perf_counter()
    catalog = await _catalog(session, user_id)
    merged = await canonical.merge(session, user_id)
    await sample_counts.rebuild(session, user_id)  # a check, kept exact
    await session.commit()
    tz = await daily_rollup.user_zone(session, user_id)
    metrics = await _sampled(session, user_id)
    days, slowest = await _rebuild_all(session, user_id, metrics, tz)
    await _stamp(session, user_id)
    report = {
        "merged": merged,
        "metrics": len(metrics),
        "days": days,
        **catalog,
        "seconds": round(time.perf_counter() - started, 1),
        "slowest": slowest,
    }
    _log.info("reconciled", user_id=user_id, **report)
    return report


async def _rebuild_all(
    session: AsyncSession,
    user_id: str,
    metrics: list[MetricDefinition],
    tz: ZoneInfo,
) -> tuple[int, list[str]]:
    """Every metric's days, and the slowest (« heart.rate 6.2 s »)."""
    days, spent = 0, []
    for metric in metrics:
        started = time.perf_counter()
        days += await daily_rollup.rebuild(session, user_id, metric, tz)
        await session.commit()
        spent.append((time.perf_counter() - started, metric.key))
    spent.sort(reverse=True)
    return days, [f"{key} {s:.1f} s" for s, key in spent[:_SLOWEST]]


async def _stamp(session: AsyncSession, user_id: str) -> None:
    """Note the hub's version this reconcile ran on (GIT_COMMIT)."""
    commit = get_settings().git_commit
    user = await session.get(User, user_id)
    if commit and user is not None:
        user.reconciled_commit = commit
        await session.commit()


async def _catalog(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Align stored data with the HealthKit catalog (see catalog_sync)."""
    report = {
        "definitions": await catalog_sync.sync_definitions(session),
        "categories": await catalog_sync.backfill_categories(session, user_id),
        "percentages": await catalog_sync.tag_percentages(session, user_id),
    }
    await session.commit()
    return report


async def _sampled(
    session: AsyncSession, user_id: str
) -> list[MetricDefinition]:
    """Metrics for which the user has numeric raw samples."""
    ids = (
        select(HealthSample.metric_id)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.value_num.is_not(None),
        )
        .distinct()
    )
    result = await session.execute(
        select(MetricDefinition)
        .where(MetricDefinition.id.in_(ids))
        .order_by(MetricDefinition.key)
    )
    return list(result.scalars().all())
