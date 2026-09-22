"""Outlier-resistant statistics for noisy daily series.

Daily photo scores move with water, meals and posture. Medians (not
means) and the Theil-Sen slope (median of pairwise slopes, robust to up
to ~29 % of outliers) keep one bad day from faking a trend.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import median

Point = tuple[date, float]


def daily_median(samples: list[Point]) -> list[Point]:
    """Collapse several values per day into their median, sorted by day."""
    by_day: dict[date, list[float]] = {}
    for day, value in samples:
        by_day.setdefault(day, []).append(value)
    return [(day, median(by_day[day])) for day in sorted(by_day)]


def rolling_median(points: list[Point], days: int) -> list[Point]:
    """Median of each point's trailing ``days``-day window."""
    out: list[Point] = []
    for day, _ in points:
        start = day - timedelta(days=days - 1)
        window = [v for d, v in points if start <= d <= day]
        out.append((day, median(window)))
    return out


def window_median(points: list[Point], start: date, end: date) -> float | None:
    """Median of the values dated within ``[start, end]``, if any."""
    window = [v for d, v in points if start <= d <= end]
    return median(window) if window else None


def theil_sen(points: list[Point]) -> float | None:
    """Robust slope in units per day (None with < 2 distinct days)."""
    slopes = [
        (b[1] - a[1]) / (b[0] - a[0]).days
        for i, a in enumerate(points)
        for b in points[i + 1 :]
        if b[0] != a[0]
    ]
    return median(slopes) if slopes else None
