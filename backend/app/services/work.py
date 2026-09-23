"""Clock in / out and the work sessions (the raw work-hours data).

A tap (GPS or one-tap Shortcut, the assistant) clocks in or out *now*;
the web page, the assistant and the importer can also add or fix whole
sessions. Nothing logged is dropped: a departure without an arrival is
kept as a session whose start is missing, to be completed by hand. Every
change rebuilds the daily values of the days it touches (:mod:`work_days`).
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

#: Longest session accepted (48 h without leaving happens).
MAX_SESSION = timedelta(hours=72)
_TIMES = ("start_at", "end_at")
#: A lone clock-in and a lone clock-out this close are one session.
_HALF = timedelta(hours=20)
#: Where the work was done: on site, or remote.
PLACES = ("site", "remote")


async def clock(
    session: AsyncSession,
    user_id: str,
    kind: str,
    at: datetime | None,
    source: str,
    place: str = "site",
) -> dict[str, Any]:
    """Clock in (open a session) or out (close the open one).

    A repeated clock-in is ignored; a clock-in at another place (remote
    after the office) opens a new session. A clock-out closes the latest
    open session, or is kept as a session whose clock-in is missing.
    """
    tz = await user_zone(session, user_id)
    when = _instant(at, tz) if at else utcnow()
    current = await _open(session, user_id, when)
    if kind == "out" and current is not None:
        current.end_at = when
    elif (
        kind == "out"
        or current is None
        or current.place != place
        or when - utc(current.start_at or when) > work_days.OPEN_FOR
    ):
        start = None if kind == "out" else when
        end = when if kind == "out" else None
        current = WorkSession(
            id=new_uuid(), user_id=user_id, start_at=start, end_at=end,
            source=source, place=place,
        )  # fmt: skip
        session.add(current)
    await work_days.refresh(session, user_id, {_day(current, tz)}, tz)
    return work_days.view(current, tz)


async def add(
    session: AsyncSession,
    user_id: str,
    fields: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Add a session; the same start (or lone end) updates that one.

    ``place`` remote: worked from home — a session of its own, even on a
    day already worked on site (it may not overlap it).
    """
    tz = await user_zone(session, user_id)
    times = {
        k: _instant(fields[k], tz) if fields.get(k) else None for k in _TIMES
    }
    place = fields.get("place") or "site"
    row = (
        await _same(session, user_id, times, place)
        or await _other_half(session, user_id, times, place)
        or WorkSession(id=new_uuid(), user_id=user_id, place=place)
    )
    times = {k: times[k] or _utc_or_none(getattr(row, k)) for k in _TIMES}
    row.source = source
    await _apply(session, row, {**fields, **times}, tz)
    session.add(row)
    await work_days.refresh(session, user_id, {_day(row, tz)}, tz)
    return work_days.view(row, tz)


async def update(
    session: AsyncSession,
    user_id: str,
    session_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Fix a session's times or note (only the fields given).

    Times completed or changed afterwards mark the session ``edited``
    (the report says which times were typed; the page lists them to
    check and fix again).
    """
    tz = await user_zone(session, user_id)
    row = await _own(session, user_id, session_id)
    before = _day(row, tz)
    given = {k: fields[k] for k in _TIMES if k in fields}
    if given:
        row.source = "edited"
    current = {k: utc(v) if (v := getattr(row, k)) else None for k in _TIMES}
    await _apply(session, row, {**current, **fields}, tz)
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
    for key in _TIMES:
        value = fields.get(key)
        setattr(row, key, _instant(value, tz) if value else None)
    if fields.get("note") is not None:
        row.note = str(fields["note"]).strip()[:200]
    if fields.get("place") in PLACES:
        row.place = fields["place"]
    if row.start_at is None and row.end_at is None:
        raise InvalidInputError("Il faut au moins l'embauche ou la débauche.")
    if row.start_at is not None and row.end_at is not None:
        length = utc(row.end_at) - utc(row.start_at)
        if not timedelta(0) < length <= MAX_SESSION:
            raise InvalidInputError(
                "La débauche doit suivre l'embauche, 72 h au plus."
            )
    await _no_overlap(session, row, tz)


async def _no_overlap(
    session: AsyncSession, row: WorkSession, tz: ZoneInfo
) -> None:
    """Refuse a session overlapping another (a lone time is a point)."""
    mine = _span(row)
    others = await session.execute(
        select(WorkSession).where(
            WorkSession.user_id == row.user_id,
            WorkSession.id != row.id,
        ).where(
            (WorkSession.start_at.between(mine[0] - MAX_SESSION, mine[1]))
            | (WorkSession.end_at.between(mine[0], mine[1] + MAX_SESSION))
        )
    )  # fmt: skip
    for other in others.scalars():
        theirs = _span(other)
        if mine[0] < theirs[1] and theirs[0] < mine[1] or mine == theirs:
            begun = theirs[0].astimezone(tz)
            raise InvalidInputError(
                f"Chevauche la session du {begun:%d/%m/%Y %H:%M}."
            )


def _span(row: WorkSession) -> tuple[datetime, datetime]:
    """A session as an interval (a lone time: a zero-length interval)."""
    start = utc(row.start_at or row.end_at or utcnow())
    return start, utc(row.end_at or row.start_at or utcnow())


async def _same(
    session: AsyncSession, user_id: str, times: dict[str, Any], place: str
) -> WorkSession | None:
    """The session an added one replaces: same start, or same lone end."""
    query = select(WorkSession).where(
        WorkSession.user_id == user_id, WorkSession.place == place
    )
    if times["start_at"] is not None:
        query = query.where(WorkSession.start_at == times["start_at"])
    elif times["end_at"] is not None:
        query = query.where(
            WorkSession.start_at.is_(None),
            WorkSession.end_at == times["end_at"],
        )
    found = await session.execute(query.limit(1))
    return found.scalar_one_or_none()


async def _other_half(
    session: AsyncSession, user_id: str, times: dict[str, Any], place: str
) -> WorkSession | None:
    """A session missing exactly the half being added (20 h around it)."""
    start, end = times["start_at"], times["end_at"]
    if (start is None) == (end is None):
        return None
    query = select(WorkSession).where(
        WorkSession.user_id == user_id, WorkSession.place == place
    )
    if start is not None:
        query = query.where(
            WorkSession.start_at.is_(None),
            WorkSession.end_at.between(start, start + _HALF),
        ).order_by(WorkSession.end_at)
    else:
        query = query.where(
            WorkSession.end_at.is_(None),
            WorkSession.start_at.between(end - _HALF, end),
        ).order_by(WorkSession.start_at.desc())
    found = await session.execute(query.limit(1))
    return found.scalar_one_or_none()


def _utc_or_none(value: datetime | None) -> datetime | None:
    """A stored time in UTC (None stays None)."""
    return utc(value) if value else None


async def _open(
    session: AsyncSession, user_id: str, when: datetime
) -> WorkSession | None:
    """The unclosed session before ``when`` (started < 72 h before)."""
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
    """The local day a session belongs to (its start, else its end)."""
    return utc(row.start_at or row.end_at or utcnow()).astimezone(tz).date()
