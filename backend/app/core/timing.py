"""Where the time of one piece of work goes, step by step.

A sync (or any work made of steps) times each named step with
:meth:`Steps.step` and reports the milliseconds per step, in the order
they started, and the ``total`` since the start: written in the log and
kept in the audit log, to find what got slow — today or months later.
A step run several times adds up. Costs a few microseconds per step.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager


class Steps:
    """Milliseconds spent per named step of one piece of work."""

    def __init__(self) -> None:
        """Start the clock of the ``total``."""
        self._started = time.perf_counter()
        self._spent: dict[str, float] = {}

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        """Time the block under ``name`` (added to any earlier time)."""
        self._spent.setdefault(name, 0.0)
        started = time.perf_counter()
        try:
            yield
        finally:
            self._spent[name] += time.perf_counter() - started

    def report(self) -> dict[str, int]:
        """Each step's milliseconds, then ``total`` since the start."""
        total = time.perf_counter() - self._started
        spent = {name: round(s * 1000) for name, s in self._spent.items()}
        return {**spent, "total": round(total * 1000)}
