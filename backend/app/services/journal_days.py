"""The daily journal: one line per day, from what is already recorded.

Per local day, newest first:

* the night that ended that morning (:mod:`sleep_nights`): minutes
  asleep, in how many goes (blocks), awakenings, bedtime → wake-up;
* the counters: water (bottles of 1.5 L, given in litres too), coffees,
  cigarettes, pees;
* the meals noted: how many, and their energy when the AI read them;
* the medication doses: taken, and declared not taken.

The days of the period are paged (``limit`` / ``offset``): only the days
of the page are read.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.measurement import Measurement
from app.models.medication import MedicationIntake
from app.models.metric import MetricDefinition
from app.services import daily_rollup, sleep_nights

#: Counter metric → its name in a journal line.
COUNTERS = {
    "water.bottles_1_5": "water_bottles",
    "habit.coffee": "coffee",
    "habit.cigarettes": "cigarettes",
    "elimination.urination": "pee",
}
LITERS_PER_BOTTLE = 1.5


async def page(
    session: AsyncSession,
    user_id: str,
    span: tuple[date, date],
    window: tuple[int, int],
) -> dict[str, Any]:
    """The lines of ``span`` (newest first) in ``window`` (limit, offset)."""
    first, last = span
    limit, offset = window
    total = max(0, (last - first).days + 1)
    top = last - timedelta(days=offset)
    bottom = max(first, top - timedelta(days=limit - 1))
    if offset >= total:
        return {"items": [], "total": total}
    tz = await daily_rollup.user_zone(session, user_id)
    nights = await sleep_nights.nights(session, user_id, bottom, top, tz)
    counts = await _counters(session, user_id, bottom, top)
    meals = await _meals(session, user_id, bottom, top)
    meds = await _doses(session, user_id, bottom, top)
    items = []
    day = top
    while day >= bottom:
        line = _line(day, nights.get(day), counts[day], meals[day])
        items.append({**line, **meds[day]})
        day -= timedelta(days=1)
    return {"items": items, "total": total}


async def first_day(session: AsyncSession, user_id: str) -> date | None:
    """The first day with a night, a counter or a meal (None: nothing)."""
    tz = await daily_rollup.user_zone(session, user_id)
    counter = await session.scalar(
        select(func.min(Measurement.date_key))
        .join(MetricDefinition, MetricDefinition.id == Measurement.metric_id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key.in_(COUNTERS),
        )
    )
    meal = await session.scalar(
        select(func.min(Meal.date_key)).where(Meal.user_id == user_id)
    )
    night = await sleep_nights.first_day(session, user_id, tz)
    days = [d for d in (counter, meal, night) if d is not None]
    return min(days) if days else None


def _line(
    day: date,
    night: sleep_nights.Night | None,
    counts: dict[str, float],
    meals: list[float | None],
) -> dict[str, Any]:
    """One day of the journal."""
    bottles = counts.get("water_bottles")
    kcal = [k for k in meals if k is not None]
    return {
        "date": day.isoformat(),
        "sleep": sleep_nights.as_dict(night) if night else None,
        **{name: counts.get(name) for name in COUNTERS.values()},
        "water_l": round(bottles * LITERS_PER_BOTTLE, 2) if bottles else None,
        "meals": len(meals),
        "meal_kcal": round(sum(kcal)) if kcal else None,
    }


async def _counters(
    session: AsyncSession, user_id: str, first: date, last: date
) -> defaultdict[date, dict[str, float]]:
    """The day's value of each counter (one daily row per day)."""
    rows = await session.execute(
        select(
            Measurement.date_key, MetricDefinition.key, Measurement.value_num
        )
        .join(MetricDefinition, MetricDefinition.id == Measurement.metric_id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key.in_(COUNTERS),
            Measurement.date_key.between(first, last),
            Measurement.event_id.is_(None),
            Measurement.value_num.is_not(None),
        )
    )
    out: defaultdict[date, dict[str, float]] = defaultdict(dict)
    for day, key, value in rows:
        out[day][COUNTERS[key]] = float(value)
    return out


async def _meals(
    session: AsyncSession, user_id: str, first: date, last: date
) -> defaultdict[date, list[float | None]]:
    """Each day's meals, as their energy (None: not read by the AI)."""
    rows = await session.execute(
        select(Meal.date_key, Meal.analysis).where(
            Meal.user_id == user_id, Meal.date_key.between(first, last)
        )
    )
    out: defaultdict[date, list[float | None]] = defaultdict(list)
    for day, analysis in rows:
        totals = (analysis or {}).get("totals") or {}
        kcal = totals.get("energy_kcal")
        out[day].append(float(kcal) if isinstance(kcal, int | float) else None)
    return out


async def _doses(
    session: AsyncSession, user_id: str, first: date, last: date
) -> defaultdict[date, dict[str, int]]:
    """Each day's medication doses: taken and declared not taken."""
    rows = await session.execute(
        select(
            MedicationIntake.date_key,
            MedicationIntake.status,
            func.count(),
        )
        .where(
            MedicationIntake.user_id == user_id,
            MedicationIntake.date_key.between(first, last),
        )
        .group_by(MedicationIntake.date_key, MedicationIntake.status)
    )
    out: defaultdict[date, dict[str, int]] = defaultdict(
        lambda: {"meds_taken": 0, "meds_skipped": 0}
    )
    for day, state, count in rows:
        key = "meds_taken" if state == "taken" else "meds_skipped"
        out[day][key] = int(count)
    return out
