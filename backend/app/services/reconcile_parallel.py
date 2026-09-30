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
import os
import sys
from asyncio.subprocess import PIPE, Process
from collections import Counter, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import MetricDefinition
from app.services import sample_counts

#: (seconds, metric key, days) of one metric's rebuild.
Spent = tuple[float, str, int]
#: The folder holding the ``app`` package, for the processes' imports.
_ROOT = str(Path(__file__).resolve().parents[2])


@asynccontextmanager
async def started(
    user_id: str, tz: ZoneInfo, processes: int
) -> AsyncIterator[list[Process]]:
    """``processes`` processes, started now and stopped on leaving.

    On an error or a cancel they are killed: the metric each one was on
    is not committed, those already done are (as one after the other).
    """
    workers: list[Process] = []
    try:
        for _ in range(processes):
            workers.append(await _start(user_id, tz))
        yield workers
        for worker in workers:
            if worker.stdin is not None:
                worker.stdin.close()  # the ones left without a metric too
            await worker.wait()
    finally:
        for worker in workers:
            if worker.returncode is None:  # an error or a cancel
                worker.kill()
                await worker.wait()


async def rebuild(workers: list[Process], order: list[str]) -> list[Spent]:
    """Every metric's days, each metric to the first process free.

    A process that fails stops the others (see :func:`started`).
    """
    queue = deque(order)
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(_feed(w, queue)) for w in workers]
    return [spent for task in tasks for spent in task.result()]


async def largest_first(
    session: AsyncSession, user_id: str, metrics: list[MetricDefinition]
) -> list[str]:
    """The metrics' ids, the most samples first (then by key)."""
    samples: Counter[str] = Counter()
    for metric_id, _, n, _, _ in await sample_counts.of_user(session, user_id):
        samples[metric_id] += n
    ranked = sorted(metrics, key=lambda m: (-samples[m.id], m.key))
    return [metric.id for metric in ranked]


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


async def _feed(worker: Process, order: deque[str]) -> list[Spent]:
    """Give the process the next metric until none is left."""
    stdin, stdout = worker.stdin, worker.stdout
    if stdin is None or stdout is None:  # never: both are pipes
        raise RuntimeError("rollup process without pipes")
    done: list[Spent] = []
    while order:
        stdin.write(f"{order.popleft()}\n".encode())
        await stdin.drain()
        line = await stdout.readline()
        if not line:  # it stopped: its error is in the log just above
            code = await worker.wait()
            raise RuntimeError(f"rollup process stopped (exit {code})")
        seconds, key, days = json.loads(line)
        done.append((float(seconds), str(key), int(days)))
    stdin.close()
    return done
