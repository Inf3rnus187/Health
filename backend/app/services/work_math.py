"""Work-hours arithmetic: days, ISO weeks, months, periods (pure).

Overtime is counted per ISO week beyond the contract (35 h in France);
the flags follow the French Code du travail maximums: 10 h in a day,
48 h in a week.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from app.models.work import WorkSession
from app.services import work_days

#: Legal maximums used as flags (Code du travail).
MAX_DAY_HOURS = 10.0
MAX_WEEK_HOURS = 48.0
_WEEKDAYS = 5


class Off(NamedTuple):
    """A day off: its group (arret, conge, repos, autre, ferie) and share.

    ``share``: 1 for a whole day, 0.5 for a half day.
    """

    kind: str
    share: float = 1.0


class Day(NamedTuple):
    """One worked day: hours, first clock-in, last clock-out (decimal).

    ``remote``: the part of ``hours`` worked remote.
    """

    hours: float
    start: float | None
    end: float | None
    remote: float = 0.0


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
            values.get(work_days.REMOTE.key, 0.0),
        )
    return dict(sorted(days.items()))


def weeks(
    days: dict[date, Day], contract: float, off: dict[date, Off] | None = None
) -> list[dict[str, Any]]:
    """ISO weeks: hours, days worked, overtime, days off and the target.

    ``off``: days off (absences, holidays). A week's target is the
    contract less its weekdays off (35 h, 21 h with two days of sick
    leave); a week entirely off is listed with no hours.
    """
    off = off or {}
    groups: dict[date, list[Day]] = defaultdict(list)
    for day, value in days.items():
        groups[_monday(day)].append(value)
    for day in off:
        groups[_monday(day)]  # noqa: B018 - a week off shows too
    return [
        _week(monday, values, contract, off)
        for monday, values in sorted(groups.items())
    ]


def _monday(day: date) -> date:
    """The Monday of a day's ISO week."""
    return day - timedelta(days=day.weekday())


def _week(
    monday: date, values: list[Day], contract: float, off: dict[date, Off]
) -> dict[str, Any]:
    """One ISO week's numbers."""
    hours = round(sum(v.hours for v in values), 2)
    year, week, _ = monday.isocalendar()
    week_off = [off[d].kind for d in _days(monday) if d in off]
    workdays_off = sum(
        off[d].share for d in _days(monday)[:_WEEKDAYS] if d in off
    )
    target = round(contract * (_WEEKDAYS - workdays_off) / _WEEKDAYS, 2)
    return {
        "week": f"{year}-W{week:02d}",
        "monday": monday,
        "hours": hours,
        "remote": round(sum(v.remote for v in values), 2),
        "days": sum(1 for v in values if v.hours > 0),
        "overtime": round(max(0.0, hours - contract), 2),
        "over_48h": hours > MAX_WEEK_HOURS,
        "absent_days": round(workdays_off, 1),
        "absence": Counter(week_off).most_common(1)[0][0] if week_off else None,
        "target": target,
        "beyond_target": round(max(0.0, hours - target), 2),
    }


def _days(monday: date) -> list[date]:
    """The seven days of a week."""
    return [monday + timedelta(days=n) for n in range(7)]


def months(days: dict[date, Day], contract: float) -> list[dict[str, Any]]:
    """Months: hours, days worked, overtime of the weeks starting in it."""
    out: dict[str, dict[str, Any]] = {}
    for day, value in days.items():
        month = out.setdefault(
            f"{day:%Y-%m}",
            {"month": f"{day:%Y-%m}", "hours": 0.0, "remote": 0.0, "days": 0},
        )
        month["hours"] = round(month["hours"] + value.hours, 2)
        month["remote"] = round(month["remote"] + value.remote, 2)
        month["days"] += value.hours > 0
    for week in weeks(days, contract):
        target = out.get(f"{week['monday']:%Y-%m}")
        if target is not None:
            target["overtime"] = round(
                target.get("overtime", 0.0) + week["overtime"], 2
            )
    return [{"overtime": 0.0, **month} for month in out.values()]


def summary(
    days: dict[date, Day], contract: float, off: dict[date, Off] | None = None
) -> dict[str, Any]:
    """Totals, averages and legal-limit flags of a set of days.

    With ``off`` (absences, holidays), the weekly average is that of the
    full weeks worked (no day off), and the hours beyond the contract
    less the days off are counted.
    """
    worked = {d: v for d, v in days.items() if v.hours > 0}
    listed = weeks(days, contract, off)
    longest = max(worked.items(), key=lambda item: item[1].hours, default=None)
    total = round(sum(v.hours for v in worked.values()), 2)
    return {
        "total_hours": total,
        "days_worked": len(worked),
        "avg_day_hours": _mean([v.hours for v in worked.values()]),
        "avg_start": clock_text(_mean([v.start for v in days.values()])),
        "avg_end": clock_text(_mean([v.end for v in days.values()])),
        "longest_day": (
            {"date": longest[0], "hours": longest[1].hours} if longest else None
        ),
        "days_over_10h": sum(v.hours > MAX_DAY_HOURS for v in worked.values()),
        "weeks_over_48h": sum(w["over_48h"] for w in listed),
        "overtime_hours": round(sum(w["overtime"] for w in listed), 2),
        **_off_part(worked, listed, off or {}),
        **_remote_part(worked),
    }


def _remote_part(worked: dict[date, Day]) -> dict[str, Any]:
    """Hours worked remote, and the days they came on top of the site."""
    remote = {d: v for d, v in worked.items() if v.remote > 0}
    return {
        "remote_hours": round(sum(v.remote for v in remote.values()), 2),
        "remote_days": len(remote),
        "remote_after_site": [
            d for d, v in remote.items() if v.hours - v.remote > 0
        ],
    }


def _off_part(
    worked: dict[date, Day], listed: list[dict[str, Any]], off: dict[date, Off]
) -> dict[str, Any]:
    """What the days off change: averages, target, work while off."""
    weeks_worked = [w for w in listed if w["hours"] > 0]
    full = [w for w in weeks_worked if not w["absent_days"]]
    return {
        "avg_week_hours": _mean([w["hours"] for w in full or weeks_worked]),
        "full_weeks": len(full),
        "beyond_target_hours": round(
            sum(w["beyond_target"] for w in listed), 2
        ),
        "worked_while_off": [  # a whole day off (not a public holiday)
            {"date": d, "kind": off[d].kind, "hours": v.hours}
            for d, v in worked.items()
            if d in off and off[d].kind != "ferie" and off[d].share >= 1
        ],
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
