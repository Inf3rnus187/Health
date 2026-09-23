"""The work ↔ health file: one gathering for the page, the MCP and the PDF.

For a period: every calendar day (work of the day, the night after it,
the day's health values, the absence it falls in), the work summary and
legal landmarks, the sleep correlations, weeks / months / years, the
absences with the work and the evidence inside them, the evidence list
and where every number comes from.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.meal import Meal
from app.models.work import Absence, Evidence, WorkSession
from app.services import (
    absences,
    evidence,
    measurements,
    sleep_nights,
    work_absence,
    work_corr,
    work_days,
    work_legal,
    work_math,
    work_traces,
)
from app.services.daily_rollup import user_zone
from app.services.sleep_nights import Night
from app.services.timed_entries import utc


async def gather(
    session: AsyncSession,
    user_id: str,
    first: date,
    last: date,
    contract: float,
) -> dict[str, Any]:
    """Everything about work and health between two days."""
    tz = await user_zone(session, user_id)
    rows = await work_days.sessions_of(session, user_id, first, last, tz)
    days = work_math.daily(rows, tz)
    nights = await sleep_nights.nights(
        session, user_id, first, last + timedelta(days=1), tz
    )
    leaves = await absences.list_absences(session, user_id, first, last)
    items = await evidence.list_items(session, user_id, first, last, tz)
    health = await _health(session, user_id, first, last)
    marks = work_traces.per_day(items, tz)
    table = _rows(first, last, (rows, days, nights, health, leaves, marks), tz)
    scores = await _scores(session, items)
    off = work_absence.day_map(leaves, first, last)
    return {
        "start": first,
        "end": last,
        "contract_hours": contract,
        **_assemble(rows, (days, off), table, contract, tz),
        "traces": work_traces.summary(table, scores),
        "absences": [_absence(a, table, items, tz) for a in leaves],
        "evidence": [_item(e, leaves, tz) for e in items],
        "days": table,
    }


def _assemble(
    rows: list[WorkSession],
    worked: tuple[dict[date, work_math.Day], dict[date, work_math.Off]],
    table: list[dict[str, Any]],
    contract: float,
    tz: ZoneInfo,
) -> dict[str, Any]:
    """Sources, work summary, landmarks, sleep and period tables."""
    days, off = worked
    return {
        "sources": _sources(rows, table),
        "work": {
            **work_math.summary(days, contract, off),
            "absences": work_absence.counts(off),
        },
        "legal": _legal(rows, days, contract, tz),
        "sleep": {
            "correlations": work_corr.correlations(table),
            "bands": work_corr.bands(table),
        },
        "weeks": work_corr.periods(table, "week", contract),
        "months": work_corr.periods(table, "month", contract),
        "years": work_corr.periods(table, "year", contract),
    }


def _rows(
    first: date,
    last: date,
    data: tuple[Any, ...],
    tz: ZoneInfo,
) -> list[dict[str, Any]]:
    """One row per calendar day."""
    rows, days, nights, health, leaves, marks = data
    partial = {
        work_days.view(r, tz)["date_key"]
        for r in rows
        if r.start_at is None or r.end_at is None
    }
    out = []
    day = first
    while day <= last:
        row = _row(day, days.get(day), day in partial, nights, health, leaves)
        out.append({**row, "traces": marks.get(day, [])})
        day += timedelta(days=1)
    return out


def _row(
    day: date,
    work: work_math.Day | None,
    partial: bool,
    nights: dict[date, Night],
    health: dict[str, dict[date, float]],
    leaves: list[Absence],
) -> dict[str, Any]:
    """A day's work, the night after it and its health values."""
    night = nights.get(day + timedelta(days=1))
    return {
        "date": day,
        "weekday": day.weekday(),
        "worked": work is not None,
        "partial": partial,
        "hours": work.hours if work and work.hours > 0 else None,
        "remote": work.remote if work and work.remote > 0 else None,
        "start": work.start if work else None,
        "end": work.end if work else None,
        "night": sleep_nights.as_dict(night) if night else None,
        "health": {k: v[day] for k, v in health.items() if day in v},
        "absence": next((a.kind for a in leaves if a.day_share(day)), None),
        "absence_share": max((a.day_share(day) for a in leaves), default=0),
    }


def _legal(
    rows: list[WorkSession],
    days: dict[date, work_math.Day],
    contract: float,
    tz: ZoneInfo,
) -> dict[str, Any]:
    """Legal landmarks, with the 12-week averages over 44 h."""
    weeks = work_math.weeks(days, contract)
    return {
        **work_legal.landmarks(rows, days, tz),
        "over_44h_12_weeks": work_legal.rolling_average(weeks),
    }


def _sources(
    rows: list[WorkSession], table: list[dict[str, Any]]
) -> dict[str, Any]:
    """Where the numbers come from, and what is missing."""
    nights = [r["night"] for r in table if r["night"]]
    worked = [r for r in table if r["worked"]]
    return {
        "sessions": len(rows),
        "by_source": dict(Counter(r.source for r in rows)),
        "missing_start": sum(1 for r in rows if r.start_at is None),
        "missing_end": sum(1 for r in rows if r.end_at is None),
        "nights": len(nights),
        "nights_by_source": dict(
            Counter(n["source"].split(":")[0] for n in nights)
        ),
        "worked_days_without_night": sum(1 for r in worked if not r["night"]),
    }


#: An absence's span: days, half days, length.
_SPAN = ("start_date", "end_date", "start_half", "end_half", "days")


def _absence(
    leave: Absence,
    table: list[dict[str, Any]],
    items: list[Evidence],
    tz: ZoneInfo,
) -> dict[str, Any]:
    """An absence with the work done and the evidence logged inside it."""
    inside = [
        r for r in table if leave.start_date <= r["date"] <= leave.end_date
    ]
    proofs = [e for e in items if _within(e, leave, tz)]
    calls = [e for e in proofs if e.kind == "appel"]
    return {
        "id": leave.id,
        **{k: getattr(leave, k) for k in _SPAN},
        "kind": leave.kind,
        "label": absences.KINDS.get(leave.kind, leave.kind),
        "cause": leave.cause,
        "note": leave.note,
        "worked_days": [r["date"] for r in inside if r["worked"]],
        "worked_hours": round(sum(r["hours"] or 0 for r in inside), 2),
        "evidence": len(proofs),
        "traces": sum(1 for e in proofs if e.kind in evidence.TRACES),
        "calls": sum(e.count for e in calls),
        "calls_on_sundays": sum(
            e.count for e in calls
            if utc(e.occurred_at).astimezone(tz).weekday() == 6  # noqa: PLR2004
        ),
    }  # fmt: skip


def _item(
    item: Evidence, leaves: list[Absence], tz: ZoneInfo
) -> dict[str, Any]:
    """An evidence item for the file."""
    return {
        "id": item.id,
        "occurred_at": utc(item.occurred_at).astimezone(tz),
        "kind": item.kind,
        "label": evidence.KINDS.get(item.kind, item.kind),
        "title": item.title,
        "description": item.description,
        "count": item.count,
        "file_name": item.file_name,
        "media_type": item.media_type,
        "sha256": item.sha256,
        "during_absence": any(_within(item, a, tz) for a in leaves),
    }


def _within(item: Evidence, leave: Absence, tz: ZoneInfo) -> bool:
    """Whether an item happened during an absence."""
    day = utc(item.occurred_at).astimezone(tz).date()
    return leave.start_date <= day <= leave.end_date


async def _scores(
    session: AsyncSession, items: list[Evidence]
) -> dict[str, float]:
    """The AI score of the meals logged from deliveries / purchases."""
    ids = {e.meal_id for e in items if e.meal_id}
    if not ids:
        return {}
    rows = await session.execute(select(Meal).where(Meal.id.in_(ids)))
    out = {}
    for meal in rows.scalars():
        score = (meal.analysis or {}).get("score")
        if isinstance(score, int | float):
            out[meal.id] = float(score)
    return out


async def _health(
    session: AsyncSession, user_id: str, first: date, last: date
) -> dict[str, dict[date, float]]:
    """The daily health values used by the file, by key then day."""
    out: dict[str, dict[date, float]] = {}
    for key in work_corr.HEALTH:
        try:
            rows = await measurements.query(
                session, user_id, metric_key=key, start=first, end=last
            )
        except NotFoundError:
            continue
        out[key] = {
            r.date_key: r.value_num for r in rows if r.value_num is not None
        }
    return out
