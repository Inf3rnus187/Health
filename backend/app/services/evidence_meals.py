"""Meals as recorded, for a report: how many, what they held, how noted.

Over the period: meals and days with a meal, per meal type, the meals
read by the AI (share), the daily means over the days with a read meal
(energy, protein, carbohydrates, sugars, fat, saturated fat, fibre,
sodium), the AI scores (mean, lowest, highest, spread), where the values
came from (the user's labels, the Ciqual table, estimated), the foods of
« Mes aliments » eaten most, per month, and the meals entered more than
three hours after being eaten.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.services.timed_entries import utc

NUTRIENTS = (
    "energy_kcal", "protein_g", "carbs_g", "sugars_g", "fat_g",
    "sat_fat_g", "fiber_g", "sodium_mg",
)  # fmt: skip
LATE_ENTRY = timedelta(hours=3)
#: Score bands: (upper bound excluded, label).
_BANDS = ((4.0, "0-3"), (7.0, "4-6"))
_TOP = 10


async def meals(
    session: AsyncSession, user_id: str, span: tuple[date, date]
) -> dict[str, Any]:
    """The period's meals as facts (empty dict: no meal)."""
    rows = await session.execute(
        select(Meal).where(
            Meal.user_id == user_id, Meal.date_key.between(span[0], span[1])
        )
    )
    found = list(rows.scalars())
    if not found:
        return {}
    read = [m for m in found if _totals(m)]
    return {
        "meals": len(found),
        "days_with_meals": len({m.date_key for m in found}),
        "by_type": dict(Counter(m.meal_type for m in found)),
        "analysed": len(read),
        "daily_means": _daily_means(read),
        "scores": _scores(read),
        "sources": dict(Counter(_source(i) for m in read for i in _items(m))),
        "top_foods": _top_foods(read),
        "months": _months(found),
        "entered_late": sum(1 for m in found if _late(m)),
        "with_photo": sum(1 for m in found if m.photo_path),
    }


def _totals(meal: Meal) -> dict[str, Any]:
    """The meal's checked totals ({} when not read)."""
    if meal.analysis_status != "done":
        return {}
    totals = (meal.analysis or {}).get("totals")
    return totals if isinstance(totals, dict) else {}


def _items(meal: Meal) -> list[dict[str, Any]]:
    """The meal's foods as read."""
    items = (meal.analysis or {}).get("items")
    return (
        [i for i in items if isinstance(i, dict)]
        if isinstance(items, list)
        else []
    )


def _source(item: dict[str, Any]) -> str:
    """Where a food's values came from."""
    return str(item.get("source") or "estimé")


def _daily_means(read: list[Meal]) -> dict[str, Any]:
    """Per nutrient: the mean of the days' sums (days with a read meal)."""
    days: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for meal in read:
        for key in NUTRIENTS:
            value = _totals(meal).get(key)
            if isinstance(value, int | float):
                days[meal.date_key][key] += float(value)
    if not days:
        return {}
    means = {
        k: round(sum(d[k] for d in days.values()) / len(days), 1)
        for k in NUTRIENTS
    }
    return {"days": len(days), **means}


def _scores(read: list[Meal]) -> dict[str, Any]:
    """The AI scores: mean, lowest, highest, and how many per band."""
    scores = [
        float(s)
        for m in read
        if isinstance(s := (m.analysis or {}).get("score"), int | float)
    ]
    if not scores:
        return {}
    bands = Counter(_band(s) for s in scores)
    return {
        "count": len(scores),
        "mean": round(sum(scores) / len(scores), 1),
        "lowest": min(scores),
        "highest": max(scores),
        "bands": dict(bands),
    }


def _band(score: float) -> str:
    """« 0-3 », « 4-6 » or « 7-10 »."""
    return next((label for top, label in _BANDS if score < top), "7-10")


def _top_foods(read: list[Meal]) -> list[dict[str, Any]]:
    """The foods of « Mes aliments » eaten most (meals, grams)."""
    count: Counter[str] = Counter()
    grams: defaultdict[str, float] = defaultdict(float)
    for meal in read:
        for item in _items(meal):
            if item.get("source") == "étiquette":
                count[str(item["name"])] += 1
                grams[str(item["name"])] += float(item.get("grams") or 0)
    return [
        {"name": name, "meals": n, "grams": round(grams[name])}
        for name, n in count.most_common(_TOP)
    ]


def _months(found: list[Meal]) -> list[dict[str, Any]]:
    """Per month: meals, days with a read meal, mean energy of those days."""
    months: dict[date, list[Meal]] = defaultdict(list)
    for meal in found:
        months[meal.date_key.replace(day=1)].append(meal)
    out = []
    for start in sorted(months):
        means = _daily_means([m for m in months[start] if _totals(m)])
        out.append({"start": start.isoformat(), "meals": len(months[start]),
                    "analysed_days": means.get("days", 0),
                    "energy_kcal": means.get("energy_kcal")})  # fmt: skip
    return out


def _late(meal: Meal) -> bool:
    """Entered more than three hours after it was eaten."""
    return utc(meal.created_at) - utc(meal.eaten_at) > LATE_ENTRY
