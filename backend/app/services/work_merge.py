"""Two sessions of the same work made one.

A clock-in and a clock-out never paired (an embauche at 09:02 left
alone, a débauche at 19:12 with no embauche), or two parts of a day
without a real break: the session kept takes the earliest clock-in and
the latest clock-out, the other is deleted, and the note says so. Same
place only (on site with on site, remote with remote); the result must
still be 72 h at most and overlap no third session.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.work import WorkSession
from app.services import work
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc

_TIMES = ("start_at", "end_at")


async def merge(
    session: AsyncSession,
    user_id: str,
    ids: tuple[str, str],
    typed: dict[str, datetime | None] | None = None,
) -> dict[str, Any]:
    """Make ``ids[1]`` part of ``ids[0]``: first clock-in → last out.

    ``typed``: times just typed for the kept session, used instead of
    its stored ones (extending 03/04 back to 02/04 12:01 over the
    session of 02/04 gives 02/04 12:01 → 03/04 21:22).
    """
    keep_id, other_id = ids
    if keep_id == other_id:
        raise InvalidInputError("Choisis une autre session à réunir.")
    keep = await _own(session, user_id, keep_id)
    other = await _own(session, user_id, other_id)
    if keep.place != other.place:
        raise InvalidInputError(
            "Une session sur place et une à distance ne se réunissent pas."
        )
    tz = await user_zone(session, user_id)
    mine = [
        _instant((typed or {}).get(k), tz) or getattr(keep, k) for k in _TIMES
    ]
    starts = [utc(t) for t in (mine[0], other.start_at) if t]
    ends = [utc(t) for t in (mine[1], other.end_at) if t]
    if not starts or not ends:
        raise InvalidInputError("Il faut une embauche et une débauche.")
    note = " · ".join(
        p for p in (keep.note, other.note, _joined(other, tz)) if p
    )[:200]
    await work.delete(session, user_id, other_id)
    fields = {"start_at": min(starts), "end_at": max(ends), "note": note}
    return await work.update(session, user_id, keep_id, fields)


def _instant(at: datetime | None, tz: ZoneInfo) -> datetime | None:
    """A typed time in UTC (without offset: the user's local time)."""
    if at is None:
        return None
    return (at if at.tzinfo else at.replace(tzinfo=tz)).astimezone(UTC)


def _joined(row: WorkSession, tz: ZoneInfo) -> str:
    """What the deleted session held: « réunie avec 09:02 → ? »."""
    start, end = (
        f"{utc(at).astimezone(tz):%H:%M}" if at else "?"
        for at in (row.start_at, row.end_at)
    )
    return f"réunie avec {start} → {end}"


async def _own(
    session: AsyncSession, user_id: str, session_id: str
) -> WorkSession:
    """One of the user's sessions or NotFoundError."""
    row = await session.get(WorkSession, session_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Work session not found")
    return row
