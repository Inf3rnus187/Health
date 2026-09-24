"""The catalogue foods of a meal, and their label values in its reading.

A meal's foods are those the user picked, plus those its description
names (the food's name, or one of its aliases: « riz sachet »). Their
grams: the form's, else what the description says (:mod:`meal_quantity`:
« 2 tomates » = 2 × the food's unit). The model is told their label
values and grams as authoritative, and its answer is then corrected: a
catalogue food's nutrients come from its label for the grams eaten (else
the model's estimate, else the package's weight); a picked food the
model forgot is added.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food import Food
from app.models.meal import Meal
from app.services import foods as food_service
from app.services.meal_quantity import grams_in
from app.services.text_norm import singular, tokens

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
            picked.append((food, entry.get("grams") or grams_in(food, said)))
    taken = {food.id for food, _ in picked}
    named = [f for f in known if f.id not in taken and named_in(f, said)]
    return picked + [(food, grams_in(food, said)) for food in named]


def named_in(food: Food, text: str) -> bool:
    """Whether ``text`` names the food (all words of its name, or an alias)."""
    words = set(_plain(text).split())
    name = [w for w in _plain(food.name).split() if len(w) > 2]  # noqa: PLR2004
    if name and all(w in words for w in name):
        return True
    said = f" {_plain(text)} "
    aliases = [_plain(a) for a in food.aliases.split(",")]
    return any(a and f" {a} " in said for a in aliases)


def context(portions: list[Portion]) -> list[dict[str, Any]]:
    """What the prompt says of each food (its label values)."""
    return [
        {
            "id": food.id,
            "name": f"{food.name} ({food.brand})" if food.brand else food.name,
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
    return next((p for p in free if named_in(p[0], str(item["name"]))), None)


def _labelled(portion: Portion, eaten: Any) -> dict[str, Any]:
    """An item computed from the label for the grams eaten."""
    food, grams = portion
    amount = float(grams or (eaten if eaten else 0) or food.package_g or 100)
    ratio = amount / 100
    label = food.per_100g
    values = {k: round(float(label.get(k) or 0) * ratio, 1) for k in NUTRIENTS}
    energy = label.get("energy_kcal")
    if energy is None:
        energy = 4 * (label.get("protein_g", 0) + label.get("carbs_g", 0))
        energy += 9 * label.get("fat_g", 0) + 2 * label.get("fiber_g", 0)
    return {
        "name": food.name[:80],
        "grams": amount,
        "energy_kcal": round(float(energy) * ratio, 1),
        **values,
        "food_id": food.id,
        "source": "étiquette",
    }


def _plain(text: str) -> str:
    """Lower case, no accents, singular words (« Tomates » → « tomate »)."""
    return " ".join(singular(w) for w in tokens(text))
