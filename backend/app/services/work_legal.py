"""Work-time landmarks of the French Code du travail, read from sessions.

Facts only, no legal judgement: daily rest under 11 h between two
working days, days spread over 13 h (first clock-in → last clock-out),
long sessions (12 h and more), a 12-week average over 44 h, Sundays and
public holidays worked, night hours (21:00-06:00), the longest run of
consecutive working days.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.models.work import WorkSession
from app.services.timed_entries import utc
from app.services.work_math import Day

MIN_REST_H = 11.0
MAX_SPREAD_H = 13.0
LONG_SESSION_H = 12.0
MAX_12W_AVG_H = 44.0
_NIGHT = (time(21, 0), time(6, 0))
_SUNDAY = 6
_WEEKS = 12
Span = tuple[datetime, datetime]


def landmarks(
    rows: list[WorkSession], days: dict[date, Day], tz: ZoneInfo
) -> dict[str, Any]:
    """Every landmark over the sessions and worked days given."""
    spans = sorted(
        (utc(r.start_at), utc(r.end_at))
        for r in rows
        if r.start_at is not None and r.end_at is not None
    )
    worked = sorted(days)
    feasts = {d for year in {d.year for d in worked} for d in holidays(year)}
    return {
        "short_rests": _short_rests(spans, tz),
        "spread_over_13h": _spreads(days),
        "long_sessions": _long(spans, tz),
        "sundays": [d for d in worked if d.weekday() == _SUNDAY],
        "holidays": [d for d in worked if d in feasts],
        "night_hours": round(sum(_night_hours(s, tz) for s in spans), 2),
        "max_consecutive_days": _longest_run(worked),
    }


def rolling_average(weeks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """12-week windows averaging over 44 h (weeks off count as 0 h)."""
    if not weeks:
        return []
    hours = {w["monday"]: w["hours"] for w in weeks}
    first, last = min(hours), max(hours)
    count = (last - first).days // 7 + 1
    mondays = [first + timedelta(weeks=i) for i in range(count)]
    series = [hours.get(m, 0.0) for m in mondays]
    windows = []
    for i in range(len(series) - _WEEKS + 1):
        average = sum(series[i : i + _WEEKS]) / _WEEKS
        if average > MAX_12W_AVG_H:
            windows.append({"from": mondays[i], "average": round(average, 2)})
    return windows


def holidays(year: int) -> set[date]:
    """French public holidays of a year (mainland)."""
    easter = _easter(year)
    fixed = [
        (1, 1),
        (5, 1),
        (5, 8),
        (7, 14),
        (8, 15),
        (11, 1),
        (11, 11),
        (12, 25),
    ]
    moving = [easter + timedelta(days=n) for n in (1, 39, 50)]
    return {date(year, m, d) for m, d in fixed} | set(moving)


def _short_rests(spans: list[Span], tz: ZoneInfo) -> list[dict[str, Any]]:
    """Rests under 11 h between a clock-out and the next day's clock-in."""
    out = []
    for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
        other_day = start.astimezone(tz).date() != end.astimezone(tz).date()
        rest = (start - end).total_seconds() / 3600
        if other_day and 0 <= rest < MIN_REST_H:
            day = start.astimezone(tz).date()
            out.append({"date": day, "rest_hours": round(rest, 2)})
    return out


def _spreads(days: dict[date, Day]) -> list[dict[str, Any]]:
    """Days whose first clock-in → last clock-out exceeds 13 h."""
    return [
        {"date": day, "hours": round(v.end - v.start, 2)}
        for day, v in days.items()
        if v.start is not None
        and v.end is not None
        and v.end - v.start > MAX_SPREAD_H
    ]


def _long(spans: list[Span], tz: ZoneInfo) -> list[dict[str, Any]]:
    """Sessions of 12 h and more (48 h without leaving shows here)."""
    out = []
    for start, end in spans:
        hours = (end - start).total_seconds() / 3600
        if hours >= LONG_SESSION_H:
            day = start.astimezone(tz).date()
            out.append({"date": day, "hours": round(hours, 2)})
    return out


def _night_hours(span: Span, tz: ZoneInfo) -> float:
    """Hours of a session between 21:00 and 06:00 local."""
    start, end = (t.astimezone(tz) for t in span)
    total, day = 0.0, start.date() - timedelta(days=1)
    while day <= end.date():
        night = (
            datetime.combine(day, _NIGHT[0], tzinfo=tz),
            datetime.combine(day + timedelta(days=1), _NIGHT[1], tzinfo=tz),
        )
        overlap = min(end, night[1]) - max(start, night[0])
        total += max(overlap.total_seconds(), 0) / 3600
        day += timedelta(days=1)
    return total


def _longest_run(days: list[date]) -> int:
    """The longest run of consecutive calendar days in ``days``."""
    best = run = 0
    previous: date | None = None
    for day in days:
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best, previous = max(best, run), day
    return best


def _easter(year: int) -> date:
    """Easter Sunday (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)
