"""Where the time of one piece of work goes, step by step.

A sync (or any work made of steps) times each named step with
:meth:`Steps.step`, or what happened since the last step with
:meth:`Steps.lap`, and reports the milliseconds per step, in the order
they started, and the ``total`` since the start: written in the log and
kept in the audit log, to find what got slow — today or months later.
A step run several times adds up. Costs about a microsecond per step.

:func:`request_steps` starts the clock when the request arrived (the
access log's start), so the time before the route runs is counted too:
the body received, read as JSON.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from starlette.requests import Request


class Steps:
    """Milliseconds spent per named step of one piece of work."""

    def __init__(self, started: float | None = None) -> None:
        """Start the clock (``started``: an earlier ``perf_counter``)."""
        self._started = time.perf_counter() if started is None else started
        self._mark = self._started
        self._spent: dict[str, float] = {}

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        """Time the block under ``name`` (added to any earlier time)."""
        self._spent.setdefault(name, 0.0)
        started = time.perf_counter()
        try:
            yield
        finally:
            self._mark = time.perf_counter()
            self._spent[name] += self._mark - started

    def lap(self, name: str, at: float | None = None) -> None:
        """Count under ``name`` the time from the last step to ``at``/now."""
        at = time.perf_counter() if at is None else at
        self._spent[name] = self._spent.get(name, 0.0) + at - self._mark
        self._mark = at

    def report(self) -> dict[str, int]:
        """Each step's milliseconds, then ``total`` since the start."""
        total = time.perf_counter() - self._started
        spent = {name: round(s * 1000) for name, s in self._spent.items()}
        return {**spent, "total": round(total * 1000)}


async def request_steps(request: Request) -> Steps:
    """A clock started when the request arrived (a FastAPI dependency).

    FastAPI reads the body as JSON before any dependency: ``receive`` is
    the body coming in (from the access log's start to its last part),
    ``json`` reading it. Without the access log (a test), both are 0.
    """
    state = request.scope.get("state", {})
    now = time.perf_counter()
    started = state.get("started", now)
    steps = Steps(started)
    steps.lap("receive", state.get("received", started))
    steps.lap("json", now)
    return steps
