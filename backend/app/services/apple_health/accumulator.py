"""Fold a stream of samples into one value per metric key and day.

Apple exports thousands of raw samples per day; the fact table keeps a
single value per metric/day (§5.3). This aggregates in constant memory
per (metric, day) cell, using each metric's declared aggregation.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from app.services.apple_health.spec import AGG_BY_KEY


@dataclass
class _Cell:
    """Running aggregation state for one metric/day bucket."""

    agg: str
    acc: float
    count: int


def _fold(cell: _Cell, value: float) -> None:
    """Fold one more value into an existing cell."""
    if cell.agg in {"sum", "avg"}:
        cell.acc += value
        cell.count += 1
    elif cell.agg == "min":
        cell.acc = min(cell.acc, value)
    elif cell.agg == "max":
        cell.acc = max(cell.acc, value)
    else:
        cell.acc = value


def _value(cell: _Cell) -> float:
    """Return the finished value for a cell."""
    if cell.agg == "avg" and cell.count:
        return cell.acc / cell.count
    return cell.acc


class DailyAggregator:
    """Accumulate samples into one value per (metric key, day)."""

    def __init__(self) -> None:
        """Start with no buckets."""
        self._cells: dict[tuple[str, date], _Cell] = {}

    def add(self, key: str, day: date, value: float) -> None:
        """Add one sample, creating or folding its daily cell."""
        cell = self._cells.get((key, day))
        if cell is not None:
            _fold(cell, value)
            return
        agg = AGG_BY_KEY.get(key, "last")
        self._cells[(key, day)] = _Cell(agg, value, 1)

    def results(self) -> Iterator[tuple[str, date, float]]:
        """Yield each ``(metric key, day, value)`` bucket."""
        for (key, day), cell in self._cells.items():
            yield key, day, _value(cell)
