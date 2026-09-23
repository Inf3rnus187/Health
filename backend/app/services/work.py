"""Clock in / out and the work sessions (the raw work-hours data).

A tap (GPS or one-tap Shortcut, the assistant) clocks in or out *now*;
the web page, the assistant and the importer can also add or fix whole
sessions. Every change rebuilds the daily values of the days it touches
(:mod:`work_days`).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.base import new_uuid, utcnow
from app.models.work import WorkSession
from app.services import work_days
from app.services.daily_rollup import user_zone
from app.services.timed_entries import utc

#: Longest believable session; an older open one is left to fix by hand.
MAX_SESSION = timedelta(hours=24)


async def clock(
    session: AsyncSession,
    user_id: str,
    kind: str,
    at: datetime | None,
    source: str,
) -> dict[str, Any]:
    """Clock in (open a session) or out (close the open one)."""
    tz = await user_zone(session, user_id)
    when = _instant(at, tz) if at else utcnow()
    current = await _open(session, user_id, when)
    if kind == "out":
        current = _close(current, when)
    elif current is None:  # already clocked in: a repeated tap is ignored
        current = WorkSession(
            id=new_uuid(), user_id=user_id, start_at=when, source=source
        )
        session.add(current)
    await work_days.refresh(session, user_id, {_day(current, tz)}, tz)
    return work_days.view(current, tz)


async def add(
    session: AsyncSession,
    user_id: str,
    fields: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Add a session (same start as an existing one: that one is updated)."""
    tz = await user_zone(session, user_id)
    start = _instant(fields["start_at"], tz)
    found = await session.execute(
        select(WorkSession).where(
            WorkSession.user_id == user_id, WorkSession.start_at == start
        )
    )
    row = found.scalar_one_or_none() or WorkSession(
        id=new_uuid(), user_id=user_id, start_at=start
    )
    row.source = source
    await _apply(session, row, fields, tz)
    session.add(row)
    await work_days.refresh(session, user_id, {_day(row, tz)}, tz)
    return work_days.view(row, tz)


async def update(
    session: AsyncSession,
    user_id: str,
    session_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Fix a session's times or note (only the fields given)."""
    tz = await user_zone(session, user_id)
    row = await _own(session, user_id, session_id)
    before = _day(row, tz)
    start = fields.get("start_at") or utc(row.start_at)
    await _apply(session, row, {**fields, "start_at": start}, tz)
    await work_days.refresh(session, user_id, {before, _day(row, tz)}, tz)
    return work_days.view(row, tz)


async def delete(session: AsyncSession, user_id: str, session_id: str) -> None:
    """Delete a session and rebuild its day."""
    tz = await user_zone(session, user_id)
    row = await _own(session, user_id, session_id)
    day = _day(row, tz)
    await session.delete(row)
    await work_days.refresh(session, user_id, {day}, tz)


async def list_sessions(
    session: AsyncSession, user_id: str, first: date, last: date
) -> list[dict[str, Any]]:
    """Sessions of the local days ``first``..``last``, newest first."""
    tz = await user_zone(session, user_id)
    rows = await work_days.sessions_of(session, user_id, first, last, tz)
    return [work_days.view(row, tz) for row in reversed(rows)]


async def _apply(
    session: AsyncSession,
    row: WorkSession,
    fields: dict[str, Any],
    tz: ZoneInfo,
) -> None:
    """Set times and note, refusing impossible or overlapping sessions."""
    row.start_at = _instant(fields["start_at"], tz)
    if "end_at" in fields:
        end = fields["end_at"]
        row.end_at = _instant(end, tz) if end else None
    if fields.get("note") is not None:
        row.note = str(fields["note"]).strip()[:200]
    if row.end_at is not None:
        length = utc(row.end_at) - utc(row.start_at)
        if not timedelta(0) < length <= MAX_SESSION:
            raise InvalidInputError(
                "La débauche doit suivre l'embauche, 24 h au plus."
            )
    await _no_overlap(session, row, tz)


async def _no_overlap(
    session: AsyncSession, row: WorkSession, tz: ZoneInfo
) -> None:
    """Refuse a session that overlaps another one of the user."""
    start = utc(row.start_at)
    end = utc(row.end_at) if row.end_at else start + timedelta(minutes=1)
    others = await session.execute(
        select(WorkSession).where(
            WorkSession.user_id == row.user_id,
            WorkSession.id != row.id,
            WorkSession.start_at < end,
            WorkSession.start_at >= start - MAX_SESSION,
        )
    )
    for other in others.scalars():
        other_end = utc(other.end_at) if other.end_at else utc(other.start_at)
        if utc(other.start_at) == start or other_end > start:
            begun = utc(other.start_at).astimezone(tz)
            raise InvalidInputError(
                f"Chevauche la session commencée le {begun:%d/%m/%Y %H:%M}."
            )


def _close(current: WorkSession | None, when: datetime) -> WorkSession:
    """Close the open session at ``when`` (none open: an error)."""
    if current is None:
        raise InvalidInputError(
            "Aucune embauche en cours (moins de 24 h) : ajoutez la "
            "session avec ses deux heures."
        )
    current.end_at = when
    return current


async def _open(
    session: AsyncSession, user_id: str, when: datetime
) -> WorkSession | None:
    """The session still open at ``when`` (started < 24 h before)."""
    rows = await session.execute(
        select(WorkSession)
        .where(
            WorkSession.user_id == user_id,
            WorkSession.end_at.is_(None),
            WorkSession.start_at <= when,
            WorkSession.start_at >= when - MAX_SESSION,
        )
        .order_by(WorkSession.start_at.desc())
        .limit(1)
    )
    return rows.scalar_one_or_none()


async def _own(
    session: AsyncSession, user_id: str, session_id: str
) -> WorkSession:
    """One of the user's sessions or NotFoundError."""
    row = await session.get(WorkSession, session_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Work session not found")
    return row


def _instant(at: datetime, tz: ZoneInfo) -> datetime:
    """An input time in UTC (a time without offset is the user's local)."""
    return (at.replace(tzinfo=tz) if at.tzinfo is None else at).astimezone(UTC)


def _day(row: WorkSession, tz: ZoneInfo) -> date:
    """The local day a session belongs to (its start)."""
    return utc(row.start_at).astimezone(tz).date()
