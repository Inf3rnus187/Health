"""Rolling windows by bisection give the plain window's numbers."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import fmean, median

import pytest
from app.services import robust_stats
from app.services.aggregation import rolling

REDUCE = {
    "sum": sum,
    "min": min,
    "max": max,
    "last": lambda values: values[-1],
    "avg": fmean,
}


def _points(step: int) -> list[tuple[date, float]]:
    """Gaps, several values on one day (i and i + 250), out of order."""
    first = date(2024, 1, 1)
    return [
        (first + timedelta(days=i * step % 250 * 2), 40 + i * 7919 % 800 / 10)
        for i in range(300)
    ]


def _plain(
    points: list[tuple[date, float]], window: int, agg: str
) -> list[tuple[date, float]]:
    """Every point reads the whole series (the former way)."""
    ordered = sorted(points)
    out = []
    for day, _ in ordered:
        start = day - timedelta(days=window - 1)
        chunk = [v for d, v in ordered if start <= d <= day]
        out.append((day, REDUCE[agg](chunk)))
    return out


@pytest.mark.parametrize("agg", sorted(REDUCE))
@pytest.mark.parametrize("window", [1, 7, 30])
def test_rolling_equals_the_plain_window(agg: str, window: int) -> None:
    points = _points(37)
    assert rolling(points, window, agg) == _plain(points, window, agg)


def test_rolling_median_equals_the_plain_window() -> None:
    points = robust_stats.daily_median(_points(41))
    plain = [
        (day, median([v for d, v in points if day - timedelta(6) <= d <= day]))
        for day, _ in points
    ]
    assert robust_stats.rolling_median(points, 7) == plain
