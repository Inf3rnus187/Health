"""Two sessions of the same work made one.

A clock-in and a clock-out never paired (an embauche at 09:02 left
alone, a débauche at 19:12 with no embauche), or two parts of a day
without a real break: the session kept takes the earliest clock-in and
the latest clock-out, the other is deleted, and the note says so. Same
place only (on site with on site, remote with remote); the result must
still be 72 h at most and overlap no third session.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.work import WorkSession
from app.services import work
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc


async def merge(
    session: AsyncSession, user_id: str, keep_id: str, other_id: str
) -> dict[str, Any]:
    """Make ``other_id`` part of ``keep_id``: first clock-in → last out."""
    if keep_id == other_id:
        raise InvalidInputError("Choisis une autre session à réunir.")
    keep = await _own(session, user_id, keep_id)
    other = await _own(session, user_id, other_id)
    if keep.place != other.place:
        raise InvalidInputError(
            "Une session sur place et une à distance ne se réunissent pas."
        )
    starts = [utc(r.start_at) for r in (keep, other) if r.start_at]
    ends = [utc(r.end_at) for r in (keep, other) if r.end_at]
    if not starts or not ends:
        raise InvalidInputError("Il faut une embauche et une débauche.")
    tz = await user_zone(session, user_id)
    note = " · ".join(
        p for p in (keep.note, other.note, _joined(other, tz)) if p
    )[:200]
    await work.delete(session, user_id, other_id)
    fields = {"start_at": min(starts), "end_at": max(ends), "note": note}
    return await work.update(session, user_id, keep_id, fields)


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
