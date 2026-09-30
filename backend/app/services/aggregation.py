"""Pure rolling-window aggregation over daily values (§5.3).

Rolling averages/derived series are computed on read, never stored, so
there is exactly one source of truth for every raw value.
"""

from __future__ import annotations

from datetime import date, timedelta
from math import fsum


def _apply(values: list[float], agg: str) -> float:
    """Reduce ``values`` with the requested aggregation."""
    if agg == "sum":
        return sum(values)
    if agg == "min":
        return min(values)
    if agg == "max":
        return max(values)
    if agg == "last":
        return values[-1]
    return fsum(values) / len(values)  # what statistics.fmean computes


def rolling(
    points: list[tuple[date, float]], window: int, agg: str
) -> list[tuple[date, float]]:
    """Return the trailing-``window`` ``agg`` for each day present.

    The window slides along the sorted days (its first and past-the-end
    indexes only move forward): each point reads only its own window,
    the values of every source of its day included.
    """
    ordered = sorted(points)
    days = [d for d, _ in ordered]
    values = [v for _, v in ordered]
    span = timedelta(days=window - 1)
    out: list[tuple[date, float]] = []
    start = end = 0
    for index, day in enumerate(days):
        end = max(end, index + 1)
        while end < len(days) and days[end] == day:
            end += 1
        while days[start] < day - span:
            start += 1
        out.append((day, _apply(values[start:end], agg)))
    return out
