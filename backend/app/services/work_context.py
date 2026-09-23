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
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    items = await evidence.list_items(session, user_id)
    days = [v["date_key"] for v in todo]
    nights = await sleep_nights.nights(
        session, user_id, min(days), max(days) + timedelta(days=1), tz
    )
    out = []
    for view in sorted(todo, key=lambda v: v["date_key"], reverse=True):
        context = await _context(
            session, user_id, view, (items, nights, usual), tz
        )
        day = [v for v in views if v["date_key"] == view["date_key"]]
        context["others"] = [_other(view, o, tz) for o in day if o is not view]
        out.append({**view, "context": context})
    return out


async def _context(
    session: AsyncSession,
    user_id: str,
    view: dict[str, Any],
    data: tuple[list[Evidence], dict[date, Any], dict[str, Any]],
    tz: ZoneInfo,
) -> dict[str, Any]:
    """What else says when the day started or ended."""
    items, nights, usual = data
    day = view["date_key"]
    wanted = "end" if view["status"] == "missing_end" else "start"
    seen = _seen(items, day, wanted, tz)
    woke, slept = nights.get(day), nights.get(day + timedelta(days=1))
    return {
        "missing": wanted,
        "has_proof": bool(seen),
        "evidence": seen,
        "wake_time": _clock(woke.wake_time) if woke else None,
        "bedtime": _clock(slept.bedtime) if slept else None,
        "activity": await _activity(session, user_id, day, tz),
        "usual": {
            "weekday": _DAYS[day.weekday()],
            "that_weekday": usual[wanted].get(day.weekday()),
            "overall": usual[wanted].get("all"),
        },
    }


def _seen(
    items: list[Evidence], day: date, wanted: str, tz: ZoneInfo
) -> list[dict[str, Any]]:
    """Proofs and traces of the day, and stays covering it.

    A missing clock-out also gets the next morning's (a taxi at 03:47).
    """
    out = []
    for item in items:
        at = utc(item.occurred_at).astimezone(tz)
        end = utc(item.ended_at).astimezone(tz) if item.ended_at else None
        next_morning = (
            wanted == "end"
            and at.date() == day + timedelta(days=1)
            and at.hour < _MORNING
        )
        covers = end is not None and at.date() <= day <= end.date()
        if at.date() == day or next_morning or covers:
            out.append(_item(item, at, end))
    out.sort(key=lambda e: e.pop("sort"))
    return out


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
        "sort": at.isoformat(),
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
    session: AsyncSession, user_id: str, day: date, tz: ZoneInfo
) -> dict[str, str | None]:
    """The first and last steps of the day (Apple Health)."""
    try:
        metric = await metrics.get_metric(session, "activity.steps")
    except Exception:  # noqa: BLE001 - no steps metric: no activity
        return {"first": None, "last": None}
    start, end = day_bounds(day, tz)
    found = await session.execute(
        select(
            func.min(HealthSample.start_at), func.max(HealthSample.end_at)
        ).where(
            HealthSample.user_id == user_id,
            HealthSample.metric_id == metric.id,
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
