"""Clocking in or out on the one-tap counter path (``/sync/tally``).

Every Shortcut follows one rule: ``{"metric": key}``. For work the keys
are ``work.start`` (clock in now, on site), ``work.remote_start`` (clock
in now, remote) and ``work.end`` (clock out now; ``work.remote_end`` is
the same).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.services import work, work_days
from app.services.daily_rollup import user_zone

#: Tally key → clock direction and place.
KINDS = {
    work_days.START.key: ("in", "site"),
    work_days.END.key: ("out", "site"),
    "work.remote_start": ("in", "remote"),
    "work.remote_end": ("out", "remote"),
}


async def tap(
    session: AsyncSession,
    user_id: str,
    metric_key: str,
    amount: float,
    day: date,
) -> tuple[float, float, str]:
    """Clock in or out now; today's hours before and after, and a line."""
    tz = await user_zone(session, user_id)
    today = utcnow().astimezone(tz).date()
    if amount != 1 or day != today:
        raise InvalidInputError(
            f"{metric_key}: a tap clocks in or out now; fix another time "
            "on the Travail page"
        )
    before = await _hours(session, user_id, today, tz)
    kind, place = KINDS[metric_key]
    row = await work.clock(session, user_id, kind, None, "tap", place)
    after = await _hours(session, user_id, today, tz)
    return before, after, _line(row, after, tz)


def _line(row: dict[str, Any], after: float, tz: ZoneInfo) -> str:
    """The notification: what was logged and the day's hours."""
    if row["end_at"] is None:
        where = " à distance" if row["place"] == "remote" else ""
        return f"Embauche{where} {row['start_at'].astimezone(tz):%H:%M}"
    worked = int(round(after * 60))
    text = (
        f"Débauche {row['end_at'].astimezone(tz):%H:%M} — "
        f"{worked // 60} h {worked % 60:02d} aujourd'hui"
    )
    if row["start_at"] is None:
        text += " (embauche non pointée : à compléter)"
    return text


async def _hours(
    session: AsyncSession, user_id: str, day: date, tz: ZoneInfo
) -> float:
    """Hours worked on ``day`` (closed sessions)."""
    rows = await work_days.sessions_of(session, user_id, day, day, tz)
    return work_days.day_values(rows, day, tz).get(work_days.HOURS.key, 0.0)
