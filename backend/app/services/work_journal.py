"""One line per day: the night, the work, the absence, the proofs.

What the Travail page opens on. For each local day: the night before it
(asleep, awakenings, wake-up), the first clock-in and the last
clock-out, the hours worked (the remote part apart), the bedtime that
evening, the absence or public holiday, the proofs and traces of the
day — and whether something is left to complete.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Evidence, WorkSession
from app.services import (
    absences,
    evidence,
    sleep_nights,
    work_absence,
    work_days,
)
from app.services.daily_rollup import user_zone
from app.services.sleep_nights import Night
from app.services.timed_entries import utc
from app.services.work_math import Off


async def journal(
    session: AsyncSession, user_id: str, first: date, last: date
) -> list[dict[str, Any]]:
    """Every day from ``first`` to ``last``, in order."""
    tz = await user_zone(session, user_id)
    rows = await work_days.sessions_of(session, user_id, first, last, tz)
    nights = await sleep_nights.nights(
        session, user_id, first, last + timedelta(days=1), tz
    )
    leaves = await absences.list_absences(session, user_id, first, last)
    off = work_absence.day_map(leaves, first, last)
    items = await evidence.list_items(session, user_id, first, last, tz)
    work, proofs = _work(rows, tz), _proofs(items, tz)
    out = []
    day = first
    while day <= last:
        facts = (work.get(day), off.get(day), proofs.get(day, []))
        out.append(_day(day, nights, facts, tz))
        day += timedelta(days=1)
    return out


def _work(rows: list[WorkSession], tz: ZoneInfo) -> dict[date, dict[str, Any]]:
    """The sessions of each day, summed up."""
    groups: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        view = work_days.view(row, tz)
        groups[view["date_key"]].append(view)
    return {day: _summed(day, views, tz) for day, views in groups.items()}


def _summed(
    day: date, views: list[dict[str, Any]], tz: ZoneInfo
) -> dict[str, Any]:
    """First clock-in, last clock-out, hours (remote apart), state."""
    starts = [v["start_at"] for v in views if v["start_at"]]
    ends = [v["end_at"] for v in views if v["end_at"]]
    done = [v for v in views if v["hours"] is not None]
    states = {v["status"] for v in views}
    return {
        "start": _clock(min(starts), day, tz) if starts else None,
        "end": _clock(max(ends), day, tz) if ends else None,
        "hours": round(sum(v["hours"] for v in done), 2) if done else None,
        "remote": round(
            sum(v["hours"] for v in done if v["place"] == "remote"), 2
        ),
        "sessions": len(views),
        "state": "a_completer"
        if states & {"missing_start", "missing_end"}
        else ("en_cours" if "open" in states else "complet"),
    }


def _clock(at: datetime, day: date, tz: ZoneInfo) -> str:
    """``HH:MM`` of an instant, ``+1`` when it falls the next day."""
    local = utc(at).astimezone(tz)
    return f"{local:%H:%M}" + (" +1" if local.date() > day else "")


def _proofs(
    items: list[Evidence], tz: ZoneInfo
) -> dict[date, list[dict[str, Any]]]:
    """The proofs and traces of each local day."""
    out: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        at = utc(item.occurred_at).astimezone(tz)
        known = item.time_known is not False
        out[at.date()].append(
            {
                "id": item.id,
                "kind": item.kind,
                "label": evidence.KINDS.get(item.kind, item.kind),
                "time": f"{at:%H:%M}" if known else None,
                "title": item.title or item.place,
                "amount": item.amount,
                "file_name": item.file_name,
            }
        )
    return out


def _day(
    day: date,
    nights: dict[date, Night],
    facts: tuple[dict[str, Any] | None, Off | None, list[dict[str, Any]]],
    tz: ZoneInfo,
) -> dict[str, Any]:
    """One day's line."""
    work, off, proofs = facts
    before, after = nights.get(day), nights.get(day + timedelta(days=1))
    return {
        "date": day,
        "weekday": day.weekday(),
        "sleep_min": round(before.asleep_min) if before else None,
        "awakenings": before.awakenings if before else None,
        "wake_time": _hhmm(before.wake_time, tz) if before else None,
        "bedtime": _hhmm(after.bedtime, tz) if after else None,
        **(work or {"start": None, "end": None, "hours": None,
                    "remote": 0.0, "sessions": 0, "state": None}),
        "absence": off.kind if off else None,
        "absence_share": off.share if off else 0.0,
        "proofs": proofs,
    }  # fmt: skip


def _hhmm(at: datetime | None, tz: ZoneInfo) -> str | None:
    """``HH:MM`` in the user's zone."""
    if at is None:
        return None
    local = at.astimezone(tz) if at.tzinfo else at
    return f"{local:%H:%M}"
