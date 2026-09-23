"""Work-hours arithmetic: days, ISO weeks, months, periods (pure).

Overtime is counted per ISO week beyond the contract (35 h in France);
the flags follow the French Code du travail maximums: 10 h in a day,
48 h in a week.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from app.models.work import WorkSession
from app.services import work_days

#: Legal maximums used as flags (Code du travail).
MAX_DAY_HOURS = 10.0
MAX_WEEK_HOURS = 48.0


class Day(NamedTuple):
    """One worked day: hours, first clock-in, last clock-out (decimal)."""

    hours: float
    start: float | None
    end: float | None


def daily(rows: list[WorkSession], tz: ZoneInfo) -> dict[date, Day]:
    """Group sessions by local day into worked days."""
    groups: dict[date, list[WorkSession]] = defaultdict(list)
    for row in rows:
        groups[work_days.view(row, tz)["date_key"]].append(row)
    days = {}
    for day, group in groups.items():
        values = work_days.day_values(group, day, tz)
        days[day] = Day(
            values.get(work_days.HOURS.key, 0.0),
            values.get(work_days.START.key),
            values.get(work_days.END.key),
        )
    return dict(sorted(days.items()))


def weeks(days: dict[date, Day], contract: float) -> list[dict[str, Any]]:
    """ISO weeks: hours, days worked, overtime beyond the contract."""
    groups: dict[date, list[Day]] = defaultdict(list)
    for day, value in days.items():
        groups[day - timedelta(days=day.weekday())].append(value)
    out = []
    for monday, values in sorted(groups.items()):
        hours = round(sum(v.hours for v in values), 2)
        year, week, _ = monday.isocalendar()
        out.append(
            {
                "week": f"{year}-W{week:02d}",
                "monday": monday,
                "hours": hours,
                "days": sum(1 for v in values if v.hours > 0),
                "overtime": round(max(0.0, hours - contract), 2),
                "over_48h": hours > MAX_WEEK_HOURS,
            }
        )
    return out


def months(days: dict[date, Day], contract: float) -> list[dict[str, Any]]:
    """Months: hours, days worked, overtime of the weeks starting in it."""
    out: dict[str, dict[str, Any]] = {}
    for day, value in days.items():
        month = out.setdefault(
            f"{day:%Y-%m}", {"month": f"{day:%Y-%m}", "hours": 0.0, "days": 0}
        )
        month["hours"] = round(month["hours"] + value.hours, 2)
        month["days"] += value.hours > 0
    for week in weeks(days, contract):
        target = out.get(f"{week['monday']:%Y-%m}")
        if target is not None:
            target["overtime"] = round(
                target.get("overtime", 0.0) + week["overtime"], 2
            )
    return [{"overtime": 0.0, **month} for month in out.values()]


def summary(days: dict[date, Day], contract: float) -> dict[str, Any]:
    """Totals, averages and legal-limit flags of a set of days."""
    worked = {d: v for d, v in days.items() if v.hours > 0}
    listed = weeks(days, contract)
    longest = max(worked.items(), key=lambda item: item[1].hours, default=None)
    total = round(sum(v.hours for v in worked.values()), 2)
    return {
        "total_hours": total,
        "days_worked": len(worked),
        "avg_day_hours": _mean([v.hours for v in worked.values()]),
        "avg_week_hours": _mean([w["hours"] for w in listed]),
        "avg_start": clock_text(_mean([v.start for v in days.values()])),
        "avg_end": clock_text(_mean([v.end for v in days.values()])),
        "longest_day": (
            {"date": longest[0], "hours": longest[1].hours} if longest else None
        ),
        "days_over_10h": sum(v.hours > MAX_DAY_HOURS for v in worked.values()),
        "weeks_over_48h": sum(w["over_48h"] for w in listed),
        "overtime_hours": round(sum(w["overtime"] for w in listed), 2),
    }


def clock_text(hour: float | None) -> str | None:
    """Decimal hours of the day as HH:MM (25.5 → 01:30 +1)."""
    if hour is None:
        return None
    minutes = int(round(hour * 60))
    text = f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"
    return f"{text} +1" if minutes >= 24 * 60 else text


def _mean(values: list[float | None]) -> float | None:
    """The mean of the known values (None if none)."""
    known = [v for v in values if v is not None]
    return round(fmean(known), 2) if known else None
