"""When and how the period's entries were made: the proof of recording.

A value typed the same minute is worth more than one typed a week
later. From the audit log (every counter tap, with the day it counts
for) and the rows themselves (doses, meals): per counter, per
treatment, for meals — how many were entered at the time, the same day,
or later, and through which channel (the web page, an iPhone Shortcut —
a token —, MCP, an import).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.meal import Meal
from app.models.medication import MedicationIntake
from app.services.daily_rollup import user_zone
from app.services.timed_entries import day_bounds, utc

#: The channel names of the audit log, as a reader says them.
CHANNELS = {"api": "site", "web": "site", "token": "raccourci"}
_HOUR, _MEAL_WINDOW = timedelta(hours=1), timedelta(hours=3)


async def trace(
    session: AsyncSession, user_id: str, span: tuple[date, date]
) -> dict[str, Any]:
    """Counters, doses and meals of ``span``: when and how entered."""
    zone = await user_zone(session, user_id)
    return {
        "counters": await _counters(session, user_id, span, zone),
        "medications": await _doses(session, user_id, span, zone),
        "meals": await _meals(session, user_id, span, zone),
    }


async def _counters(
    session: AsyncSession, user_id: str, span: tuple[date, date], zone: Any
) -> list[dict[str, Any]]:
    """Per counter: taps, entered the same day or later, channels."""
    low = day_bounds(span[0], zone)[0]
    rows = await session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user_id,
            AuditLog.entity == "measurement",
            AuditLog.action == "add",
            AuditLog.created_at >= low,  # a late entry counts too
        )
    )
    taps: dict[str, list[tuple[date, datetime, str]]] = defaultdict(list)
    for row in rows.scalars():
        info = row.payload or {}
        day = _day(info.get("date"))
        if day and span[0] <= day <= span[1] and info.get("metric"):
            taps[str(info["metric"])].append((day, row.created_at, row.source))
    return [_summary(key, found, zone) for key, found in sorted(taps.items())]


def _summary(
    key: str, found: list[tuple[date, datetime, str]], zone: Any
) -> dict[str, Any]:
    """One counter's taps: same day, later, earlier, channels."""
    entered = [(day, utc(at).astimezone(zone).date()) for day, at, _ in found]
    return {
        "metric": key,
        "entries": len(found),
        "same_day": sum(1 for day, on in entered if on == day),
        "later": sum(1 for day, on in entered if on > day),
        "channels": dict(Counter(CHANNELS.get(s, s) for *_, s in found)),
    }


async def _doses(
    session: AsyncSession, user_id: str, span: tuple[date, date], zone: Any
) -> dict[str, Any]:
    """The doses: entered within the hour, the same day, later."""
    rows = await session.execute(
        select(MedicationIntake).where(
            MedicationIntake.user_id == user_id,
            MedicationIntake.date_key.between(span[0], span[1]),
        )
    )
    found = [
        (utc(d.taken_at), utc(d.created_at), d.source) for d in rows.scalars()
    ]
    return _timing(found, _HOUR, zone)


async def _meals(
    session: AsyncSession, user_id: str, span: tuple[date, date], zone: Any
) -> dict[str, Any]:
    """The meals: entered within three hours, the same day, later."""
    rows = await session.execute(
        select(Meal).where(
            Meal.user_id == user_id, Meal.date_key.between(span[0], span[1])
        )
    )
    found = [(utc(m.eaten_at), utc(m.created_at), "") for m in rows.scalars()]
    return _timing(found, _MEAL_WINDOW, zone)


def _timing(
    found: list[tuple[datetime, datetime, str]], window: timedelta, zone: Any
) -> dict[str, Any]:
    """Entries at the time (within ``window``), the same day, later."""
    if not found:
        return {}
    local = [(a.astimezone(zone), b.astimezone(zone), s) for a, b, s in found]
    soon = sum(1 for at, on, _ in local if on - at <= window)
    same = sum(1 for at, on, _ in local if on.date() == at.date())
    out: dict[str, Any] = {
        "entries": len(found),
        "at_the_time": soon,
        "same_day": same,
        "later": sum(1 for at, on, _ in local if on.date() > at.date()),
        "window_hours": window.total_seconds() / 3600,
    }
    channels = Counter(CHANNELS.get(s, s) for *_, s in local if s)
    if channels:
        out["channels"] = dict(channels)
    return out


def _day(value: Any) -> date | None:
    """An ISO day, or None."""
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
