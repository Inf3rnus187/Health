"""The catalogue foods of a meal, and their label values in its reading.

A meal's foods are those the user picked, plus those its description
names (:mod:`food_match`: its name, an alias « riz sachet », or « un
pavé de saumon » for « Saumon sauvage rose »). Their grams: the form's,
else what the description says (:mod:`meal_quantity`: « 2 tomates » = 2
× the food's unit), else its usual portion (``portion_g``). The model is
told their label values and grams as authoritative, and its answer is
then corrected: a catalogue food's nutrients come from its label for the
grams eaten (else the model's estimate, else the package's weight); the
model's own line for such a food (« Saumon » from the Ciqual table) is
replaced, a second one dropped; a food the model forgot is added.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food import Food
from app.models.meal import Meal
from app.services import foods as food_service
from app.services.food_match import fits, named
from app.services.meal_quantity import grams_in

#: The label values copied onto an item (energy apart: from the label).
NUTRIENTS = (
    "protein_g", "carbs_g", "sugars_g", "fat_g", "sat_fat_g", "fiber_g",
    "sodium_mg",
)  # fmt: skip
Portion = tuple[Food, float | None]


async def of_meal(session: AsyncSession, meal: Meal) -> list[Portion]:
    """The foods picked for the meal, then those its description names."""
    known = await food_service.list_foods(session, meal.user_id)
    by_id = {food.id: food for food in known}
    said = meal.description or ""
    picked: list[Portion] = []
    for entry in meal.foods or []:
        food = by_id.get(str(entry.get("food_id")))
        if food is not None:
            picked.append((food, entry.get("grams") or _eaten(food, said)))
    taken = {food.id for food, _ in picked}
    said_foods = [f for f in named(known, said) if f.id not in taken]
    return picked + [(food, _eaten(food, said)) for food in said_foods]


def label(food: Food) -> str:
    """How a food is shown: name, brand, package (sizes stay apart)."""
    pack = f"{food.package_g:g} g" if food.package_g else ""
    return " · ".join(b for b in (food.name, food.brand, pack) if b)[:160]


def context(portions: list[Portion]) -> list[dict[str, Any]]:
    """What the prompt says of each food (its label values)."""
    return [
        {
            "id": food.id,
            "name": label(food),
            "package_g": food.package_g,
            "unit": f"1 {food.unit_name or 'unité'} = {food.unit_g:g} g"
            if food.unit_g
            else None,
            "grams": grams,
            "per_100g": food.per_100g,
            "note": food.note,
        }
        for food, grams in portions
    ]


def apply(
    items: list[dict[str, Any]], portions: list[Portion]
) -> list[dict[str, Any]]:
    """The items with the label values of the catalogue foods."""
    out: list[dict[str, Any]] = []
    used: set[str] = set()
    for item in items:
        match = _match(item, portions, used)
        if match is None:
            if not _again(item, portions, used):
                out.append(item)
            continue
        used.add(match[0].id)
        out.append(_labelled(match, item.get("grams")))
    for food, grams in portions:
        if food.id not in used and (grams or food.package_g):
            out.append(_labelled((food, grams), None))
    return out


def _match(
    item: dict[str, Any], portions: list[Portion], used: set[str]
) -> Portion | None:
    """The catalogue food an item stands for (its id, else its name)."""
    free = [p for p in portions if p[0].id not in used]
    by_id = next((p for p in free if p[0].id == item.get("food_id")), None)
    if by_id is not None:
        return by_id
    return next((p for p in free if fits(p[0], str(item["name"]))), None)


def _again(
    item: dict[str, Any], portions: list[Portion], used: set[str]
) -> bool:
    """Whether the item is a second line for a food already counted."""
    done = [food for food, _ in portions if food.id in used]
    return any(
        food.id == item.get("food_id") or fits(food, str(item["name"]))
        for food in done
    )


def _labelled(portion: Portion, eaten: Any) -> dict[str, Any]:
    """An item computed from the label for the grams eaten."""
    food, grams = portion
    amount = float(grams or (eaten if eaten else 0) or food.package_g or 100)
    ratio = amount / 100
    per = food.per_100g
    values = {k: round(float(per.get(k) or 0) * ratio, 1) for k in NUTRIENTS}
    energy = per.get("energy_kcal")
    if energy is None:
        energy = 4 * (per.get("protein_g", 0) + per.get("carbs_g", 0))
        energy += 9 * per.get("fat_g", 0) + 2 * per.get("fiber_g", 0)
    return {
        "name": label(food),
        "grams": amount,
        "energy_kcal": round(float(energy) * ratio, 1),
        **values,
        "food_id": food.id,
        "source": "étiquette",
    }


def _eaten(food: Food, said: str) -> float | None:
    """The grams the description gives, else the usual portion."""
    return grams_in(food, said) or food.portion_g
