"""Pure rolling-window aggregation over daily values (§5.3).

Rolling averages/derived series are computed on read, never stored, so
there is exactly one source of truth for every raw value.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import date, timedelta
from statistics import fmean


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
    return fmean(values)


def rolling(
    points: list[tuple[date, float]], window: int, agg: str
) -> list[tuple[date, float]]:
    """Return the trailing-``window`` ``agg`` for each day present.

    The window's bounds are found by bisection in the sorted days: each
    point reads only its own window, not the whole series.
    """
    ordered = sorted(points)
    days = [d for d, _ in ordered]
    values = [v for _, v in ordered]
    out: list[tuple[date, float]] = []
    for day in days:
        start = bisect_left(days, day - timedelta(days=window - 1))
        chunk = values[start : bisect_right(days, day)]
        out.append((day, _apply(chunk, agg)))
    return out
