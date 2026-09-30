"""Help completing a day: what else says when you arrived or left.

For each session with a missing half: the traces and proofs of the day
(and of the next morning for a missing clock-out), the wake-up that
morning and the bedtime that night, the first and last steps of the day,
your usual clock-in / clock-out for that weekday, and the day's other
sessions (a lone clock-in to merge with, a session to clock in after).
Facts to choose from — the hub never fills a time by itself.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.health_raw import HealthSample
from app.models.work import Evidence, WorkSession
from app.services import evidence, metrics, sleep_nights, work_days
from app.services.daily_rollup import user_zone
from app.services.timed_entries import day_bounds, utc
from app.services.work_math import clock_text

_DAYS = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)
_MORNING = 12
#: Local day → (rank in the list, item, its local start, its local end).
_Items = dict[date, list[tuple[int, Evidence, datetime, datetime | None]]]
#: What the viewer shows of a proof (the file itself is fetched apart).
_SHOWN = ("place", "amount", "currency", "description", "file_name",
          "media_type", "count")  # fmt: skip


async def incomplete(
    session: AsyncSession, user_id: str
) -> list[dict[str, Any]]:
    """Every session with a missing half, newest first, with its context."""
    tz = await user_zone(session, user_id)
    rows = (await session.execute(
        select(WorkSession).where(WorkSession.user_id == user_id)
    )).scalars().all()  # fmt: skip
    views = [work_days.view(r, tz) for r in rows]
    todo = [v for v in views if v["status"] in {"missing_start", "missing_end"}]
    if not todo:
        return []
    usual = _usual([v for v in views if v["status"] == "complete"], tz)
    items = _by_day(await evidence.list_items(session, user_id), tz)
    nights = await _nights(session, user_id, [v["date_key"] for v in todo], tz)
    steps = await _steps(session)
    out = []
    for view in sorted(todo, key=lambda v: v["date_key"], reverse=True):
        context = await _context(
            session, user_id, view, _Data(items, nights, usual, steps), tz
        )
        day = [v for v in views if v["date_key"] == view["date_key"]]
        context["others"] = [_other(view, o, tz) for o in day if o is not view]
        out.append({**view, "context": context})
    return out


async def _context(
    session: AsyncSession,
    user_id: str,
    view: dict[str, Any],
    data: _Data,
    tz: ZoneInfo,
) -> dict[str, Any]:
    """What else says when the day started or ended."""
    items, nights, usual, steps = data
    day = view["date_key"]
    wanted = "end" if view["status"] == "missing_end" else "start"
    seen = _seen(items, day, wanted)
    woke, slept = nights.get(day), nights.get(day + timedelta(days=1))
    return {
        "missing": wanted,
        "has_proof": bool(seen),
        "evidence": seen,
        "wake_time": _clock(woke.wake_time) if woke else None,
        "bedtime": _clock(slept.bedtime) if slept else None,
        "activity": await _activity(session, user_id, steps, day, tz),
        "usual": {
            "weekday": _DAYS[day.weekday()],
            "that_weekday": usual[wanted].get(day.weekday()),
            "overall": usual[wanted].get("all"),
        },
    }


class _Data(NamedTuple):
    """What every day to complete is read against (read once)."""

    items: _Items
    nights: dict[date, Any]
    usual: dict[str, Any]
    steps: str | None


def _by_day(items: list[Evidence], tz: ZoneInfo) -> _Items:
    """Proofs and traces by local day (a stay: under each day it covers).

    Read once for every day to complete, not once per day.
    """
    out: _Items = defaultdict(list)
    for rank, item in enumerate(items):
        at = utc(item.occurred_at).astimezone(tz)
        end = utc(item.ended_at).astimezone(tz) if item.ended_at else None
        out[at.date()].append((rank, item, at, end))
        day = at.date() + timedelta(days=1)
        while end is not None and day <= end.date():
            out[day].append((rank, item, at, end))
            day += timedelta(days=1)
    return out


def _seen(items: _Items, day: date, wanted: str) -> list[dict[str, Any]]:
    """Proofs and traces of the day, and stays covering it.

    A missing clock-out also gets the next morning's (a taxi at 03:47).
    """
    found = {entry[0]: entry for entry in items.get(day, [])}
    if wanted == "end":
        for entry in items.get(day + timedelta(days=1), []):
            if entry[2].date() > day and entry[2].hour < _MORNING:
                found[entry[0]] = entry
    ordered = sorted(found.values(), key=lambda e: (e[2].isoformat(), e[0]))
    return [_item(item, at, end) for _, item, at, end in ordered]


async def _nights(
    session: AsyncSession, user_id: str, days: list[date], tz: ZoneInfo
) -> dict[date, Any]:
    """The nights of the days to complete and of their next days only."""
    wanted = sorted({d + timedelta(days=k) for d in days for k in (0, 1)})
    found: dict[date, Any] = {}
    first = wanted[0]
    for prev, day in zip(wanted, [*wanted[1:], None], strict=True):
        if day is None or day - prev > timedelta(days=1):
            found |= await sleep_nights.nights(
                session, user_id, first, prev, tz
            )
            first = day or prev
    return found


async def _steps(session: AsyncSession) -> str | None:
    """The steps metric's id (None without one), looked up once."""
    try:
        return (await metrics.get_metric(session, "activity.steps")).id
    except NotFoundError:
        return None


def _item(item: Evidence, at: datetime, end: datetime | None) -> dict[str, Any]:
    """One proof or trace, its times ready to pick."""
    known = item.time_known is not False
    shown = f"{at:%d/%m %H:%M}" if known else f"{at:%d/%m} (heure inconnue)"
    return {
        "id": item.id,
        "kind": item.kind,
        "label": evidence.KINDS.get(item.kind, item.kind),
        "title": item.title,
        "trace": item.kind in evidence.TRACES,
        "at": at.isoformat() if known else None,
        "end_at": end.isoformat() if end else None,
        "time": shown + (f" → {end:%d/%m %H:%M}" if end else ""),
        **{k: getattr(item, k) for k in _SHOWN},
    }


def _other(
    view: dict[str, Any], other: dict[str, Any], tz: ZoneInfo
) -> dict[str, Any]:
    """Another session of the day: its times, the one both would make.

    ``merged``: the first clock-in → the last clock-out of the two (same
    place). ``free``: for a missing clock-in, the end of a session before
    (clock in after it); for a missing clock-out, the start of a session
    after (clock out before it).
    """
    starts = [v["start_at"] for v in (view, other) if v["start_at"]]
    ends = [v["end_at"] for v in (view, other) if v["end_at"]]
    whole = bool(starts and ends) and min(starts) < max(ends)
    same = view["place"] == other["place"]
    return {
        "id": other["id"],
        "start": _clock(other["start_at"], tz),
        "end": _clock(other["end_at"], tz),
        "place": other["place"],
        "merged": f"{_clock(min(starts), tz)} → {_clock(max(ends), tz)}"
        if whole and same
        else None,
        "free": _free(view, other, tz),
    }


def _free(
    view: dict[str, Any], other: dict[str, Any], tz: ZoneInfo
) -> str | None:
    """Where the missing half may go, bounded by a whole other session."""
    if not (other["start_at"] and other["end_at"]):
        return None  # a lone time: rather merge with it
    if view["end_at"] and other["end_at"] <= view["end_at"]:
        return utc(other["end_at"]).astimezone(tz).isoformat()
    if view["start_at"] and other["start_at"] >= view["start_at"]:
        return utc(other["start_at"]).astimezone(tz).isoformat()
    return None


async def _activity(
    session: AsyncSession,
    user_id: str,
    steps: str | None,
    day: date,
    tz: ZoneInfo,
) -> dict[str, str | None]:
    """The first and last steps of the day (Apple Health)."""
    if steps is None:
        return {"first": None, "last": None}
    start, end = day_bounds(day, tz)
    found = await session.execute(
        select(
            func.min(HealthSample.start_at), func.max(HealthSample.end_at)
        ).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == steps,
            HealthSample.start_at >= start,
            HealthSample.start_at < end,
        )
    )
    first, last = found.one()
    return {"first": _clock(first, tz), "last": _clock(last, tz)}


def _usual(views: list[dict[str, Any]], tz: ZoneInfo) -> dict[str, Any]:
    """Median clock-in and clock-out, per weekday and overall."""
    out: dict[str, Any] = {}
    for key, field in (("start", "start_at"), ("end", "end_at")):
        per_day: dict[Any, list[float]] = defaultdict(list)
        for view in views:
            at = view[field].astimezone(tz)
            hour = at.hour + at.minute / 60
            per_day[view["date_key"].weekday()].append(hour)
            per_day["all"].append(hour)
        out[key] = {k: clock_text(median(v)) for k, v in per_day.items()}
    return out


def _clock(at: datetime | None, tz: ZoneInfo | None = None) -> str | None:
    """A time as HH:MM (in ``tz`` when given)."""
    if at is None:
        return None
    local = utc(at).astimezone(tz) if tz else at
    return f"{local:%H:%M}"
