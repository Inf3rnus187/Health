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
slowest metrics (``slowest``), to see where it goes on real data. Step 2
runs ``RECONCILE_PARALLEL`` metrics at a time (:mod:`reconcile_parallel`),
in processes started at the beginning, and the raw samples' counts are
rebuilt (a check) meanwhile.
"""

from __future__ import annotations

import asyncio
import time
from asyncio.subprocess import Process
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.models.user import User
from app.services import (
    canonical,
    catalog_sync,
    daily_rollup,
    reconcile_parallel,
    sample_counts,
)
from app.services.reconcile_parallel import Spent

_log = get_logger("reconcile")
#: The slowest metrics named in the log line.
_SLOWEST = 5


async def run(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Merge aliases, then rebuild every sampled metric; report counts."""
    started = time.perf_counter()
    tz = await daily_rollup.user_zone(session, user_id)
    processes = await _processes(session, user_id)
    # The processes load their code while the first steps run.
    async with reconcile_parallel.started(user_id, tz, processes) as workers:
        catalog = await _catalog(session, user_id)
        merged = await canonical.merge(session, user_id)
        await session.commit()
        metrics = await _sampled(session, user_id)
        spent = await _days(session, user_id, metrics, tz, workers)
    await _stamp(session, user_id)
    spent.sort(reverse=True)
    report = {
        "merged": merged,
        "metrics": len(metrics),
        "days": sum(n for _, _, n in spent),
        **catalog,
        "seconds": round(time.perf_counter() - started, 1),
        "slowest": [f"{key} {s:.1f} s" for s, key, _ in spent[:_SLOWEST]],
    }
    _log.info("reconciled", user_id=user_id, **report)
    return report


async def _processes(session: AsyncSession, user_id: str) -> int:
    """``RECONCILE_PARALLEL`` processes, none for 1 or for one metric."""
    wanted = get_settings().reconcile_parallel
    if wanted <= 1:
        return 0
    rows = await sample_counts.of_user(session, user_id)
    return wanted if len({row[0] for row in rows}) > 1 else 0


async def _days(
    session: AsyncSession,
    user_id: str,
    metrics: list[MetricDefinition],
    tz: ZoneInfo,
    workers: list[Process],
) -> list[Spent]:
    """Every metric's days; the raw samples' counts rebuilt (a check).

    With processes, the counts are rebuilt here while they compute the
    days; without, one after the other, here.
    """
    if not workers:
        await _recount(session, user_id)
        return [await _rebuild(session, user_id, m, tz) for m in metrics]
    order = await reconcile_parallel.largest_first(session, user_id, metrics)
    await session.commit()  # the processes write: hold nothing open
    days = asyncio.create_task(reconcile_parallel.rebuild(workers, order))
    try:
        await _recount(session, user_id)
    except BaseException:
        days.cancel()  # the processes are stopped on leaving
        raise
    return await days


async def _recount(session: AsyncSession, user_id: str) -> None:
    """The raw samples' counts rebuilt from the samples, kept exact."""
    await sample_counts.rebuild(session, user_id)
    await session.commit()  # its lock on the samples ends here


async def _rebuild(
    session: AsyncSession, user_id: str, metric: MetricDefinition, tz: ZoneInfo
) -> Spent:
    """One metric's days, committed: (seconds, key, days)."""
    started = time.perf_counter()
    days = await daily_rollup.rebuild(session, user_id, metric, tz)
    await session.commit()
    return time.perf_counter() - started, metric.key, days


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
