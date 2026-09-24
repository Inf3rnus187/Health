"""Adherence: doses planned, taken, not taken, per treatment and period.

For each treatment, over its days within the period (from its start —
or its first dose — to its end, or today):

* planned doses = days × ``doses_per_day`` (None: « as needed », no
  rate), taken, skipped (declared not taken), days complete, days with
  no record at all, the longest run of days without a dose taken;
* the rate = Σ min(taken that day, planned per day) ÷ planned;
* the usual time of the doses (median), and how many were entered more
  than an hour after being taken (typed afterwards);
* per week: planned and taken.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.models.medical import Treatment
from app.models.medication import MedicationIntake
from app.services.daily_rollup import user_zone
from app.services.timed_entries import local_day, utc

LATE_ENTRY = timedelta(hours=1)
DEFAULT_DAYS = 30


async def span(
    session: AsyncSession, user_id: str, start: date | None, end: date | None
) -> tuple[date, date]:
    """The period asked (default: the last 30 days up to today)."""
    last = end or await local_day(session, user_id, utcnow())
    first = start or last - timedelta(days=DEFAULT_DAYS - 1)
    if first > last:
        raise InvalidInputError("start is after end")
    return first, last


async def today(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    """The active treatments and today's doses (taken, not taken, last)."""
    zone = await user_zone(session, user_id)
    day = datetime.now(zone).date()
    rows = await session.execute(
        select(Treatment)
        .where(Treatment.user_id == user_id, Treatment.active.is_(True))
        .order_by(Treatment.name)
    )
    doses = await session.execute(
        select(MedicationIntake).where(
            MedicationIntake.user_id == user_id,
            MedicationIntake.date_key == day,
        )
    )
    mine: dict[str | None, list[MedicationIntake]] = {}
    for dose in doses.scalars():
        mine.setdefault(dose.treatment_id, []).append(dose)
    return [_today(t, mine.get(t.id, []), zone) for t in rows.scalars()]


def _today(
    treatment: Treatment, doses: list[MedicationIntake], zone: Any
) -> dict[str, Any]:
    """One treatment today."""
    taken = [d for d in doses if d.status == "taken"]
    last = max((utc(d.taken_at) for d in taken), default=None)
    return {
        "treatment_id": treatment.id,
        "name": treatment.name,
        "dose": treatment.dose,
        "doses_per_day": treatment.doses_per_day,
        "taken": len(taken),
        "skipped": len(doses) - len(taken),
        "last_at": last.astimezone(zone).isoformat() if last else None,
        "last_id": max(doses, key=lambda d: d.created_at).id if doses else None,
    }


async def adherence(
    session: AsyncSession, user_id: str, span: tuple[date, date]
) -> dict[str, Any]:
    """Every treatment's adherence over ``span`` (local days)."""
    zone = await user_zone(session, user_id)
    rows = await session.execute(
        select(Treatment)
        .where(Treatment.user_id == user_id)
        .order_by(Treatment.name)
    )
    intakes = await session.execute(
        select(MedicationIntake).where(MedicationIntake.user_id == user_id)
    )
    by_treatment: dict[str | None, list[MedicationIntake]] = {}
    for intake in intakes.scalars():
        by_treatment.setdefault(intake.treatment_id, []).append(intake)
    items = []
    for treatment in rows.scalars():
        doses = by_treatment.get(treatment.id, [])
        window = _window(treatment, doses, span, zone)
        if window is not None:
            items.append(_stats(treatment, doses, window, zone))
    return {
        "start": span[0].isoformat(),
        "end": span[1].isoformat(),
        "items": items,
    }


def _window(
    treatment: Treatment,
    doses: list[MedicationIntake],
    span: tuple[date, date],
    zone: Any,
) -> tuple[date, date] | None:
    """The treatment's days within the period (None: none)."""
    first = min((d.date_key for d in doses), default=None)
    created = utc(treatment.created_at).astimezone(zone).date()
    begin = treatment.start_date or min(first or created, created)
    last = max((d.date_key for d in doses), default=None)
    today = datetime.now(zone).date()
    end = treatment.end_date or (today if treatment.active else last)
    if end is None:
        return None
    start, stop = max(span[0], begin), min(span[1], end, today)
    return (start, stop) if start <= stop else None


def _stats(
    treatment: Treatment,
    doses: list[MedicationIntake],
    window: tuple[date, date],
    zone: Any,
) -> dict[str, Any]:
    """One treatment's numbers over its window."""
    inside = [d for d in doses if window[0] <= d.date_key <= window[1]]
    taken = [d for d in inside if d.status == "taken"]
    per_day = Counter(d.date_key for d in taken)
    days = (window[1] - window[0]).days + 1
    plan = treatment.doses_per_day
    return {
        "treatment_id": treatment.id,
        "name": treatment.name,
        "dose": treatment.dose,
        "doses_per_day": plan,
        "start": window[0].isoformat(),
        "end": window[1].isoformat(),
        "days": days,
        **_rate(per_day, plan, days),
        "taken": len(taken),
        "skipped": len(inside) - len(taken),
        "days_without_record": days - len({d.date_key for d in inside}),
        "longest_gap_days": _gap(per_day, window),
        "usual_time": _usual(taken, zone),
        "entered_late": sum(1 for d in inside if _late(d)),
        "weeks": _weeks(per_day, plan, window),
    }


def _rate(
    per_day: Counter[date], plan: int | None, days: int
) -> dict[str, Any]:
    """Planned doses, days complete and the rate (None: as needed)."""
    if not plan:
        return {"planned": None, "days_complete": None, "rate": None}
    kept = sum(min(n, plan) for n in per_day.values())
    return {
        "planned": plan * days,
        "days_complete": sum(1 for n in per_day.values() if n >= plan),
        "rate": round(kept / (plan * days) * 100, 1),
    }


def _gap(per_day: Counter[date], window: tuple[date, date]) -> int:
    """The longest run of days without a dose taken."""
    longest = run = 0
    day = window[0]
    while day <= window[1]:
        run = 0 if per_day.get(day) else run + 1
        longest = max(longest, run)
        day += timedelta(days=1)
    return longest


def _usual(taken: list[MedicationIntake], zone: Any) -> str | None:
    """The median local time of the doses taken (« 08:10 »)."""
    if not taken:
        return None
    minutes = [
        (at.hour * 60 + at.minute)
        for at in (utc(d.taken_at).astimezone(zone) for d in taken)
    ]
    middle = int(median(minutes))
    return f"{middle // 60:02d}:{middle % 60:02d}"


def _late(intake: MedicationIntake) -> bool:
    """Entered more than an hour after it was taken."""
    return utc(intake.created_at) - utc(intake.taken_at) > LATE_ENTRY


def _weeks(
    per_day: Counter[date], plan: int | None, window: tuple[date, date]
) -> list[dict[str, Any]]:
    """Per week (Monday): days of the window, doses planned and taken."""
    weeks: dict[date, dict[str, Any]] = {}
    day = window[0]
    while day <= window[1]:
        monday = day - timedelta(days=day.weekday())
        week = weeks.setdefault(
            monday, {"start": monday.isoformat(), "days": 0, "taken": 0}
        )
        week["days"] += 1
        week["taken"] += per_day.get(day, 0)
        day += timedelta(days=1)
    for week in weeks.values():
        week["planned"] = week["days"] * plan if plan else None
    return list(weeks.values())
