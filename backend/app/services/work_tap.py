"""Clocking in or out on the one-tap counter path (``/sync/tally``).

Every Shortcut follows one rule: ``{"metric": key}``. For work the keys
are ``work.start`` (clock in now) and ``work.end`` (clock out now).
"""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.services import work, work_days
from app.services.daily_rollup import user_zone

#: Tally key → clock direction.
KINDS = {work_days.START.key: "in", work_days.END.key: "out"}


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
    row = await work.clock(session, user_id, KINDS[metric_key], None, "tap")
    after = await _hours(session, user_id, today, tz)
    if row["end_at"] is None:
        return before, after, f"Embauche {row['start_at'].astimezone(tz):%H:%M}"
    worked = int(round(after * 60))
    return (
        before,
        after,
        (
            f"Débauche {row['end_at'].astimezone(tz):%H:%M} — "
            f"{worked // 60} h {worked % 60:02d} aujourd'hui"
        ),
    )


async def _hours(
    session: AsyncSession, user_id: str, day: date, tz: ZoneInfo
) -> float:
    """Hours worked on ``day`` (closed sessions)."""
    rows = await work_days.sessions_of(session, user_id, day, day, tz)
    return work_days.day_values(rows, day, tz).get(work_days.HOURS.key, 0.0)
