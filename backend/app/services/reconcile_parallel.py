"""The reconcile's daily values rebuilt on several processor cores.

Recomputing a metric's days is Python work on one core (reading each
sample, converting it, adding it to its day): 16.6 s for 60 metrics on
2 million samples, one metric after the other. The metrics share
nothing — each writes only its own days — so ``RECONCILE_PARALLEL``
processes rebuild them at the same time, each with its own connection
and the unchanged :func:`daily_rollup.rebuild` (same rule, same days).
The metrics with the most samples go first, each to the first process
free, so that a long one does not start alone at the end.

Each process is a program of its own (:mod:`app.cli.rollup_worker`,
``python -m``): it inherits none of the worker's connections, and does
not depend on how the reconcile was started (a worker, a script given on
Python's input…). The processes are started at the reconcile's start
(:func:`started`): they load their code (1 to 2 s) while the reconcile's
first steps run, and touch no data until given a metric. They live as
long as one reconcile and each holds one database connection.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from asyncio.subprocess import PIPE, Process
from collections import Counter, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.services import sample_counts
from app.services.daily_rollup import Span

#: (seconds, metric key, days) of one metric's rebuild.
Spent = tuple[float, str, int]
#: The folder holding the ``app`` package, for the processes' imports.
_ROOT = str(Path(__file__).resolve().parents[2])
#: Held by the reconcile whose processes run (one at a time per worker).
_CORES = asyncio.Lock()


@asynccontextmanager
async def started(
    user_id: str, tz: ZoneInfo, processes: int
) -> AsyncIterator[list[Process]]:
    """``processes`` processes, started now and stopped on leaving.

    One reconcile at a time has processes in a worker (:data:`_CORES`):
    accounts reconciled together take the cores in turn, never
    ``processes`` × accounts processes and connections. On an error or a
    cancel they are killed: the metric each one was on is not committed,
    those already done are (as one after the other).
    """
    if processes <= 0:  # computed here, one metric after the other
        yield []
        return
    async with _CORES:
        workers: list[Process] = []
        try:
            for _ in range(processes):
                workers.append(await _start(user_id, tz))
            yield workers
            for worker in workers:
                if worker.stdin is not None:
                    worker.stdin.close()  # the ones left without a metric
                await worker.wait()
        finally:
            for worker in workers:
                if worker.returncode is None:  # an error or a cancel
                    worker.kill()
                    await worker.wait()


class Piece(NamedTuple):
    """A metric, or a period of it, given to one process."""

    metric_id: str
    span: Span | None  # None: the whole metric
    samples: float  # to start the largest first
    part: str  # « 1/2 » in the log, or nothing


async def pieces(
    session: AsyncSession,
    user_id: str,
    metrics: list[MetricDefinition],
    tz: ZoneInfo,
    processes: int,
) -> list[Piece]:
    """The metrics to compute, the most samples first (then by key).

    A metric with at least ``RECONCILE_SPLIT_MIN_SAMPLES`` samples and more
    than one process's share of the account's is cut, at local midnights,
    into periods of about a share each: no process is left alone with it
    at the end while the others wait.
    """
    samples = await _samples(session, user_id)
    share = sum(samples[m.id] for m in metrics) / processes
    least = get_settings().reconcile_split_min_samples
    out: list[Piece] = []
    for metric in sorted(metrics, key=lambda m: m.key):
        n = samples[metric.id]
        cut = min(processes, math.ceil(n / share)) if n >= least else 1
        if cut > 1:
            out += await _cut(session, (user_id, metric.id), n, cut, tz)
        else:
            out.append(Piece(metric.id, None, n, ""))
    return sorted(out, key=lambda piece: -piece.samples)  # stable


async def rebuild(workers: list[Process], order: list[Piece]) -> list[Spent]:
    """Every piece's days, each to the first process free.

    A process that fails stops the others (see :func:`started`).
    """
    queue = deque(order)
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(_feed(w, queue)) for w in workers]
    return [spent for task in tasks for spent in task.result()]


async def _start(user_id: str, tz: ZoneInfo) -> Process:
    """A process of :mod:`app.cli.rollup_worker`, same environment."""
    paths = [_ROOT, os.environ.get("PYTHONPATH", "")]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, paths))}
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.cli.rollup_worker",
        user_id,
        tz.key,
        stdin=PIPE,
        stdout=PIPE,
        env=env,
    )


async def _feed(worker: Process, order: deque[Piece]) -> list[Spent]:
    """Give the process the next piece until none is left.

    One line ``METRIC_ID FIRST STOP`` per piece (``-``: no bound).
    """
    stdin, stdout = worker.stdin, worker.stdout
    if stdin is None or stdout is None:  # never: both are pipes
        raise RuntimeError("rollup process without pipes")
    done: list[Spent] = []
    while order:
        piece = order.popleft()
        first, stop = piece.span or (None, None)
        line = f"{piece.metric_id} {first or '-'} {stop or '-'}\n"
        stdin.write(line.encode())
        await stdin.drain()
        answer = await stdout.readline()
        if not answer:  # it stopped: its error is in the log just above
            code = await worker.wait()
            raise RuntimeError(f"rollup process stopped (exit {code})")
        seconds, key, days = json.loads(answer)
        done.append((float(seconds), f"{key}{piece.part}", int(days)))
    stdin.close()
    return done


async def _cut(
    session: AsyncSession,
    owner: tuple[str, str],
    samples: int,
    parts: int,
    tz: ZoneInfo,
) -> list[Piece]:
    """The metric in ``parts`` periods of about as many samples each.

    Cut at the local day of the samples at 1/parts, 2/parts… of the
    metric, found through its index (≈ 50 ms for 400 000 samples).
    """
    days: list[date] = []
    for i in range(1, parts):
        day = await _day_of(session, owner, samples * i // parts, tz)
        if day is not None and (not days or day > days[-1]):
            days.append(day)
    edges: list[date | None] = [None, *days, None]
    count = len(edges) - 1
    return [
        Piece(
            owner[1],
            (edges[i], edges[i + 1]),
            samples / count,
            _part(i, count),
        )
        for i in range(count)
    ]


async def _day_of(
    session: AsyncSession, owner: tuple[str, str], rank: int, tz: ZoneInfo
) -> date | None:
    """The local day of the metric's sample of this rank in time."""
    user_id, metric_id = owner
    at = await session.scalar(
        select(HealthSample.start_at)
        .where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric_id,
        )
        .order_by(HealthSample.start_at)
        .offset(rank)
        .limit(1)
    )
    return None if at is None else _local(at, tz)


def _part(index: int, count: int) -> str:
    """« 1/2 » in the log, nothing for a whole metric."""
    return f" {index + 1}/{count}" if count > 1 else ""


def _local(at: datetime, tz: ZoneInfo) -> date:
    """The local day of a sample time (naive: UTC, as SQLite gives)."""
    return (at if at.tzinfo else at.replace(tzinfo=UTC)).astimezone(tz).date()


async def _samples(session: AsyncSession, user_id: str) -> Counter[str]:
    """Samples per metric, from the counts the database keeps."""
    samples: Counter[str] = Counter()
    for metric_id, _, n, _, _ in await sample_counts.of_user(session, user_id):
        samples[metric_id] += n
    return samples
