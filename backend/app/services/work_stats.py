"""Work-hours statistics of a period, with the short / long term view."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import work_absence, work_days, work_math
from app.services.daily_rollup import user_zone
from app.services.work_math import Day, summary

#: The periods of the short / medium / long term view.
PERIODS = ((7, "7 jours"), (30, "30 jours"), (90, "3 mois"), (365, "1 an"))


async def stats(
    session: AsyncSession,
    user_id: str,
    first: date,
    last: date,
    contract: float,
) -> dict[str, Any]:
    """Everything the Travail page, the export and the report show.

    Days off (sick leave, holidays, rest, public holidays) are listed,
    left out of the weekly average and taken off the contract target.
    """
    tz = await user_zone(session, user_id)
    since = min(first, last - timedelta(days=364))
    rows = await work_days.sessions_of(session, user_id, since, last, tz)
    days = work_math.daily(rows, tz)
    off_all = await work_absence.days_off(session, user_id, since, last)
    inside = {d: v for d, v in days.items() if first <= d <= last}
    off = {d: k for d, k in off_all.items() if first <= d <= last}
    listed = [work_days.view(row, tz) for row in rows]
    return {
        "start": first,
        "end": last,
        "contract_hours": contract,
        "open": next((s for s in listed if s["status"] == "open"), None),
        **summary(inside, contract, off),
        "absences": work_absence.counts(off),
        "days": _days(inside, off),
        "weeks": work_math.weeks(inside, contract, off),
        "months": work_math.months(inside, contract),
        "periods": periods(days, last, contract, off_all),
    }


def _days(
    inside: dict[date, Day], off: dict[date, str]
) -> list[dict[str, Any]]:
    """Worked days and days off, in order."""
    out = []
    for day in sorted({*inside, *off}):
        value = inside.get(day, Day(0.0, None, None))
        out.append(
            {
                "date": day,
                **value._asdict(),
                "start_text": work_math.clock_text(value.start),
                "end_text": work_math.clock_text(value.end),
                "absence": off.get(day),
            }
        )
    return out


def periods(
    days: dict[date, Day], last: date, contract: float, off: dict[date, str]
) -> list[dict[str, Any]]:
    """Short / medium / long term: the last 7, 30, 90 and 365 days.

    The weekly average is per week present: weekdays off (absences,
    public holidays), and the days before the first one recorded, are
    not weeks of work.
    """
    out = []
    for length, label in PERIODS:
        first = last - timedelta(days=length - 1)
        inside = {d: v for d, v in days.items() if first <= d <= last}
        stats = summary(inside, contract)
        known = max(first, min(days, default=last))  # nothing before
        present = work_absence.present_weekdays(off, known, last)
        away = [k for d, k in off.items() if first <= d <= last]
        out.append(
            {
                "label": label,
                "days": length,
                "total_hours": stats["total_hours"],
                "days_worked": stats["days_worked"],
                "remote_hours": stats["remote_hours"],
                "absent_days": sum(1 for k in away if k != "ferie"),
                "week_average": (
                    round(stats["total_hours"] / (present / 5), 2)
                    if present
                    else None
                ),
                "overtime_hours": stats["overtime_hours"],
            }
        )
    return out
