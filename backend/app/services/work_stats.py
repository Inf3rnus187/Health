"""Work-hours statistics of a period, with the short / long term view."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import work_days, work_math
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
    """Everything the Travail page, the export and the report show."""
    tz = await user_zone(session, user_id)
    since = min(first, last - timedelta(days=364))
    rows = await work_days.sessions_of(session, user_id, since, last, tz)
    days = work_math.daily(rows, tz)
    inside = {d: v for d, v in days.items() if first <= d <= last}
    listed = [work_days.view(row, tz) for row in rows]
    return {
        "start": first,
        "end": last,
        "contract_hours": contract,
        "open": next((s for s in listed if s["status"] == "open"), None),
        **summary(inside, contract),
        "days": [
            {
                "date": d,
                **v._asdict(),
                "start_text": work_math.clock_text(v.start),
                "end_text": work_math.clock_text(v.end),
            }
            for d, v in inside.items()
        ],
        "weeks": work_math.weeks(inside, contract),
        "months": work_math.months(inside, contract),
        "periods": periods(days, last, contract),
    }


def periods(
    days: dict[date, Day], last: date, contract: float
) -> list[dict[str, Any]]:
    """Short / medium / long term: the last 7, 30, 90 and 365 days."""
    out = []
    for length, label in PERIODS:
        first = last - timedelta(days=length - 1)
        inside = {d: v for d, v in days.items() if first <= d <= last}
        stats = summary(inside, contract)
        out.append(
            {
                "label": label,
                "days": length,
                "total_hours": stats["total_hours"],
                "days_worked": stats["days_worked"],
                "week_average": round(stats["total_hours"] / (length / 7), 2),
                "overtime_hours": stats["overtime_hours"],
            }
        )
    return out
