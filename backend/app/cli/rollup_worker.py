"""One process of a parallel reconcile (:mod:`app.services.reconcile_parallel`).

Started as ``python -m app.cli.rollup_worker USER_ID ZONE`` by the
reconcile, never by hand. It reads metric ids on its input, one per
line; for each, it rebuilds the metric's days with the unchanged
:func:`daily_rollup.rebuild` on its own connection, commits, and answers
one JSON line ``[seconds, metric key, days]``. It ends with its input.
Its output holds these answers only: anything else it would print goes
to its error output, which is the worker's log.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from typing import TextIO
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from app.core.config import get_settings
from app.models.metric import MetricDefinition
from app.services import daily_rollup


def main() -> None:
    """Serve the metrics given on the input, then stop."""
    user_id, zone = sys.argv[1], sys.argv[2]
    answers, sys.stdout = sys.stdout, sys.stderr
    asyncio.run(_serve(user_id, ZoneInfo(zone), answers))


async def _serve(user_id: str, tz: ZoneInfo, answers: TextIO) -> None:
    """One metric per input line, one answer per output line."""
    engine = create_async_engine(get_settings().database_url)
    try:
        for line in sys.stdin:  # nothing else to do while waiting
            spent = await _one(engine, user_id, line.strip(), tz)
            answers.write(json.dumps(spent) + "\n")
            answers.flush()
    finally:
        await engine.dispose()


async def _one(
    engine: AsyncEngine, user_id: str, metric_id: str, tz: ZoneInfo
) -> tuple[float, str, int]:
    """The metric's days rebuilt and committed: (seconds, key, days)."""
    started = time.perf_counter()
    async with AsyncSession(
        engine, expire_on_commit=False, autoflush=False
    ) as session:
        metric = await session.get(MetricDefinition, metric_id)
        if metric is None:  # removed meanwhile: nothing to write
            return time.perf_counter() - started, metric_id, 0
        days = await daily_rollup.rebuild(session, user_id, metric, tz)
        await session.commit()
    return time.perf_counter() - started, metric.key, days


if __name__ == "__main__":
    main()
