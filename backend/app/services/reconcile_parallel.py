"""The reconcile's daily values rebuilt on several processor cores.

Recomputing a metric's days is Python work on one core (reading each
sample, converting it, adding it to its day): 16.6 s for 60 metrics on
2 million samples, one metric after the other. The metrics share
nothing — each writes only its own days — so ``RECONCILE_PARALLEL``
processes rebuild them at the same time, each with its own connection
and the unchanged :func:`daily_rollup.rebuild` (same rule, same days).
The metrics with the most samples start first, so that a long one does
not start alone at the end.

The processes are started with ``spawn``: a fresh interpreter, which
inherits none of the worker's open connections. They live as long as
one reconcile and each holds one database connection at a time.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.models.metric import MetricDefinition
from app.services import daily_rollup, sample_counts

#: (seconds, metric key, days) of one metric's rebuild.
Spent = tuple[float, str, int]


async def rebuild(
    session: AsyncSession,
    user_id: str,
    metrics: list[MetricDefinition],
    tz: ZoneInfo,
    processes: int,
) -> list[Spent]:
    """Every metric's days, ``processes`` metrics at a time."""
    order = await _largest_first(session, user_id, metrics)
    await session.commit()  # the processes write: hold nothing open
    loop = asyncio.get_running_loop()
    pool = ProcessPoolExecutor(
        min(processes, len(order)),
        mp_context=multiprocessing.get_context("spawn"),
    )
    try:
        return list(
            await asyncio.gather(
                *(
                    loop.run_in_executor(pool, one, user_id, metric_id, tz)
                    for metric_id in order
                )
            )
        )
    finally:
        await asyncio.to_thread(pool.shutdown, True, cancel_futures=True)


def one(user_id: str, metric_id: str, tz: ZoneInfo) -> Spent:
    """In a process of the pool: one metric's days, then committed."""
    return asyncio.run(_one(user_id, metric_id, tz))


async def _one(user_id: str, metric_id: str, tz: ZoneInfo) -> Spent:
    """The metric rebuilt on the process's own connection."""
    started = time.perf_counter()
    engine = create_async_engine(
        get_settings().database_url, poolclass=NullPool
    )
    try:
        async with AsyncSession(
            engine, expire_on_commit=False, autoflush=False
        ) as session:
            metric = await session.get(MetricDefinition, metric_id)
            if metric is None:  # removed meanwhile: nothing to write
                return time.perf_counter() - started, metric_id, 0
            days = await daily_rollup.rebuild(session, user_id, metric, tz)
            await session.commit()
    finally:
        await engine.dispose()
    return time.perf_counter() - started, metric.key, days


async def _largest_first(
    session: AsyncSession, user_id: str, metrics: list[MetricDefinition]
) -> list[str]:
    """The metrics' ids, the most samples first (then by key)."""
    samples: Counter[str] = Counter()
    for metric_id, _, n, _, _ in await sample_counts.of_user(session, user_id):
        samples[metric_id] += n
    ranked = sorted(metrics, key=lambda m: (-samples[m.id], m.key))
    return [metric.id for metric in ranked]
