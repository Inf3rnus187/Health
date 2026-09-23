"""Daily work values rebuilt from the sessions (one truth).

The sessions are the raw data. Each local day gets three daily values,
like any other metric (charts, dashboards, exports, reports, MCP):
``work.hours`` (hours worked, closed sessions), ``work.start`` (first
clock-in) and ``work.end`` (last clock-out), both in decimal hours of the
day (8.25 = 08:15; past midnight, 25.5 = 01:30 the next day). A session
belongs to the day it starts.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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
SPECS = (HOURS, START, END)


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
    """Sessions starting on the local days ``first``..``last``, in order."""
    start, _ = timed_entries.day_bounds(first, tz)
    _, end = timed_entries.day_bounds(last, tz)
    rows = await session.execute(
        select(WorkSession)
        .where(
            WorkSession.user_id == user_id,
            WorkSession.start_at >= start,
            WorkSession.start_at < end,
        )
        .order_by(WorkSession.start_at)
    )
    return list(rows.scalars())


def day_values(
    rows: list[WorkSession], day: date, tz: ZoneInfo
) -> dict[str, float]:
    """``work.hours`` / ``start`` / ``end`` of one day from its sessions."""
    if not rows:
        return {}
    midnight = datetime.combine(day, time.min, tzinfo=tz)
    values = {START.key: _hour(rows[0].start_at, midnight)}
    closed = [row for row in rows if row.end_at is not None]
    if closed:
        values[HOURS.key] = round(sum(hours(row) or 0 for row in closed), 2)
        values[END.key] = max(_hour(row.end_at, midnight) for row in closed)
    return values


def hours(row: WorkSession) -> float | None:
    """A session's duration in hours (None while open)."""
    if row.end_at is None:
        return None
    return (utc(row.end_at) - utc(row.start_at)).total_seconds() / 3600


def view(row: WorkSession, tz: ZoneInfo) -> dict[str, Any]:
    """A session as the API shows it: local day, times, duration."""
    duration = hours(row)
    return {
        "id": row.id,
        "date_key": utc(row.start_at).astimezone(tz).date(),
        "start_at": utc(row.start_at),
        "end_at": utc(row.end_at) if row.end_at else None,
        "hours": None if duration is None else round(duration, 2),
        "source": row.source,
        "note": row.note or "",
    }


def _hour(at: datetime | None, midnight: datetime) -> float:
    """Decimal hours since the day's local midnight."""
    if at is None:
        return 0.0
    return round((utc(at) - midnight).total_seconds() / 3600, 2)
