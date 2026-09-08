"""Pure rolling-window aggregation over daily values (§5.3).

Rolling averages/derived series are computed on read, never stored, so
there is exactly one source of truth for every raw value.
"""

from __future__ import annotations

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
    """Return the trailing-``window`` ``agg`` for each day present."""
    ordered = sorted(points)
    out: list[tuple[date, float]] = []
    for day, _ in ordered:
        start = day - timedelta(days=window - 1)
        chunk = [v for d, v in ordered if start <= d <= day]
        out.append((day, _apply(chunk, agg)))
    return out
