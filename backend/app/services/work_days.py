"""Daily work values rebuilt from the sessions (one truth).

The sessions are the raw data. Each local day gets its daily values,
like any other metric (charts, dashboards, exports, reports, MCP):
``work.hours`` (hours worked, closed sessions, remote included),
``work.remote_hours`` (the part worked remote), ``work.start`` (first
clock-in) and ``work.end`` (last clock-out), both in decimal hours of the
day (8.25 = 08:15; past midnight, 25.5 = 01:30 the next day). A session
belongs to the day it starts.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utcnow
from app.models.measurement import Measurement
from app.models.work import WorkSession
from app.schemas.measurement import MeasurementIn
from app.services import measurements, timed_entries
from app.services.apple_health.spec import MetricSpec
from app.services.timed_entries import utc

HOURS = MetricSpec(
    "work.hours", "Heures travaillées", "work", "float", "h", "sum"
)
START = MetricSpec(
    "work.start", "Heure d'embauche", "work", "float", "h", "avg"
)
END = MetricSpec("work.end", "Heure de débauche", "work", "float", "h", "avg")
REMOTE = MetricSpec(
    "work.remote_hours", "Heures à distance", "work", "float", "h", "sum"
)
SPECS = (HOURS, START, END, REMOTE)
#: A clock-in without clock-out is "at work now" this long; after it the
#: clock-out is "missing", and a new clock-in starts a new session.
OPEN_FOR = timedelta(hours=16)


async def refresh(
    session: AsyncSession, user_id: str, days: set[date], tz: ZoneInfo
) -> None:
    """Rebuild the daily work values of ``days`` (empty days cleared)."""
    if not days:
        return
    await session.flush()
    metrics = [await timed_entries.metric_for(session, s) for s in SPECS]
    for day in sorted(days):
        await session.execute(
            delete(Measurement).where(
                Measurement.user_id == user_id,
                Measurement.metric_id.in_([metric.id for metric in metrics]),
                Measurement.date_key == day,
                Measurement.event_id.is_(None),
            )
        )
        rows = await sessions_of(session, user_id, day, day, tz)
        items = [
            MeasurementIn(metric_key=key, date_key=day, value=value)
            for key, value in day_values(rows, day, tz).items()
        ]
        if items:
            await measurements.record_batch(
                session, user_id, items, source="work"
            )


async def sessions_of(
    session: AsyncSession,
    user_id: str,
    first: date,
    last: date,
    tz: ZoneInfo,
) -> list[WorkSession]:
    """Sessions of the local days ``first``..``last``, in order.

    A session belongs to the day it starts (a departure logged alone: the
    day it ends).
    """
    start, _ = timed_entries.day_bounds(first, tz)
    _, end = timed_entries.day_bounds(last, tz)
    anchor = func.coalesce(WorkSession.start_at, WorkSession.end_at)
    rows = await session.execute(
        select(WorkSession)
        .where(WorkSession.user_id == user_id, anchor >= start, anchor < end)
        .order_by(anchor)
    )
    return list(rows.scalars())


def day_values(
    rows: list[WorkSession], day: date, tz: ZoneInfo
) -> dict[str, float]:
    """``work.hours`` / ``start`` / ``end`` of one day from its sessions.

    Hours count complete sessions only; the first clock-in and the last
    clock-out are facts even when their other half is missing.
    """
    midnight = datetime.combine(day, time.min, tzinfo=tz)
    starts = [utc(r.start_at) for r in rows if r.start_at is not None]
    ends = [utc(r.end_at) for r in rows if r.end_at is not None]
    values: dict[str, float] = {}
    if starts:
        values[START.key] = _hour(min(starts), midnight)
    if ends:
        values[END.key] = _hour(max(ends), midnight)
    closed = [(r, length) for r in rows if (length := hours(r)) is not None]
    if closed:
        values[HOURS.key] = round(sum(n for _, n in closed), 2)
    remote = [n for r, n in closed if r.place == "remote"]
    if remote:
        values[REMOTE.key] = round(sum(remote), 2)
    return values


def hours(row: WorkSession) -> float | None:
    """A session's duration in hours (None while a half is missing)."""
    if row.start_at is None or row.end_at is None:
        return None
    return (utc(row.end_at) - utc(row.start_at)).total_seconds() / 3600


def view(row: WorkSession, tz: ZoneInfo) -> dict[str, Any]:
    """A session as the API shows it: local day, times, duration, status."""
    duration = hours(row)
    anchor = utc(row.start_at or row.end_at or utcnow())
    return {
        "id": row.id,
        "date_key": anchor.astimezone(tz).date(),
        "start_at": utc(row.start_at) if row.start_at else None,
        "end_at": utc(row.end_at) if row.end_at else None,
        "hours": None if duration is None else round(duration, 2),
        "status": _status(row),
        "source": row.source,
        "note": row.note or "",
        "place": row.place or "site",
    }


def _status(row: WorkSession) -> str:
    """complete, open (at work now), missing_start or missing_end."""
    if row.start_at is None:
        return "missing_start"
    if row.end_at is not None:
        return "complete"
    recent = utcnow() - utc(row.start_at) < OPEN_FOR
    return "open" if recent else "missing_end"


def _hour(at: datetime, midnight: datetime) -> float:
    """Decimal hours since the day's local midnight."""
    return round((utc(at) - midnight).total_seconds() / 3600, 2)
