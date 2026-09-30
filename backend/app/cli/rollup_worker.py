"""One process of a parallel reconcile (:mod:`app.services.reconcile_parallel`).

Started as ``python -m app.cli.rollup_worker USER_ID ZONE`` by the
reconcile, never by hand. It reads ``METRIC_ID FIRST STOP`` on its
input, one per line (a period of local days, ``-``: no bound; both
``-``: the whole metric); for each, it rebuilds those days with the
unchanged :func:`daily_rollup.rebuild` on its own connection, commits,
and answers one JSON line ``[seconds, metric key, days]``. It ends
with its input. Its output holds these answers only: anything else it
would print goes to its error output, which is the worker's log.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date
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
from app.services.daily_rollup import Span


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
            metric_id, first, stop = line.split()
            span = _span(first, stop)
            spent = await _one(engine, (user_id, metric_id), span, tz)
            answers.write(json.dumps(spent) + "\n")
            answers.flush()
    finally:
        await engine.dispose()


async def _one(
    engine: AsyncEngine,
    owner: tuple[str, str],
    span: Span | None,
    tz: ZoneInfo,
) -> tuple[float, str, int]:
    """The metric's days (of ``span``) rebuilt and committed."""
    user_id, metric_id = owner
    started = time.perf_counter()
    async with AsyncSession(
        engine, expire_on_commit=False, autoflush=False
    ) as session:
        metric = await session.get(MetricDefinition, metric_id)
        if metric is None:  # removed meanwhile: nothing to write
            return time.perf_counter() - started, metric_id, 0
        days = await daily_rollup.rebuild(
            session, user_id, metric, tz, span=span, in_table_order=True
        )
        await session.commit()
    return time.perf_counter() - started, metric.key, days


def _span(first: str, stop: str) -> Span | None:
    """The local days of a period (``-``: no bound); None: all of them."""
    if first == stop == "-":
        return None
    return (
        None if first == "-" else date.fromisoformat(first),
        None if stop == "-" else date.fromisoformat(stop),
    )


if __name__ == "__main__":
    main()
