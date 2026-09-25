"""Check the model's nutrient estimates and total them.

A food is kept only if it is physically possible: 0 < grams ≤ 1500,
no negative value, protein + carbs + fat + fibre not heavier than the
food, sugars ≤ carbs, saturated fat ≤ fat, sodium plausible. Anything
else is dropped with its reason. The model's energy is recomputed from
the macros (Atwater: 4 kcal/g protein and carbs, 9 fat, 2 fibre); a
food valued from the Ciqual table (:mod:`meal_ciqual`) keeps the
table's values and energy (only its grams are checked).
"""

from __future__ import annotations

from typing import Any

from app.services import ciqual, meal_remarks

MACROS = ("protein_g", "carbs_g", "sugars_g", "fat_g", "sat_fat_g", "fiber_g")
_MAX_GRAMS = 1500.0
_SODIUM_PER_G = 40.0  # mg per gram of food: above table salt density
#: Keys an item keeps besides its values (set by code, not the model).
_KEPT = {
    "food_id": 36,
    "ciqual": 12,
    "source": 40,
    "reference": 160,
    "grams_from": 12,
}


def check(items: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Plausible foods (energy recomputed) and the rejected ones."""
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for raw in items if isinstance(items, list) else []:
        item, reason = _item(raw)
        if item is None:
            name = str(raw.get("name", "?")) if isinstance(raw, dict) else "?"
            rejected.append({"name": name[:80], "reason": reason})
        else:
            kept.append(item)
    return kept, rejected


def totals(items: list[dict[str, Any]]) -> dict[str, float]:
    """Sum of the kept foods, energy included."""
    keys = ("grams", "energy_kcal", *MACROS, "sodium_mg")
    return {k: round(sum(i[k] for i in items), 1) for k in keys}


def assessment(
    answer: dict[str, Any],
    trusted: bool = False,
    known: meal_remarks.Known | None = None,
) -> dict[str, Any]:
    """Score (0-10), verdict and remarks, bounded and checked.

    ``trusted``: the meal has foods of « Mes aliments » (a doubt on their
    labels is cut); ``known``: what the code computed, for the numbers
    the remarks quote (:mod:`meal_remarks`).
    """
    score = _number(answer.get("score"))
    return {
        "score": None if score is None else max(0.0, min(10.0, score)),
        "verdict": meal_remarks.short(answer.get("verdict") or "") or None,
        "positives": meal_remarks.clean(
            _texts(answer.get("positives")), trusted, known
        ),
        "watch": meal_remarks.clean(
            _texts(answer.get("watch")), trusted, known
        ),
    }


def _item(raw: Any) -> tuple[dict[str, Any] | None, str]:
    """One food, or why it is rejected."""
    if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
        return None, "aliment sans nom"
    values = {k: _number(raw.get(k)) or 0.0 for k in (*MACROS, "sodium_mg")}
    grams = _number(raw.get("grams")) or 0.0
    table = _from_table(raw)
    reason = _implausible(grams, values) if not table else _quantity(grams)
    if reason:
        return None, reason
    energy = _number(raw.get("energy_kcal")) if table else None
    if energy is None:
        energy = 4 * (values["protein_g"] + values["carbs_g"])
        energy += 9 * values["fat_g"] + 2 * values["fiber_g"]
    name = str(raw["name"]).strip()[:80]
    item = {"name": name, "grams": grams, "energy_kcal": energy, **values}
    for key, size in _KEPT.items():
        if isinstance(raw.get(key), str):
            item[key] = raw[key][:size]
    return item, ""


def _from_table(raw: dict[str, Any]) -> bool:
    """Whether the item's values were taken from the Ciqual table."""
    code = raw.get("ciqual")
    return (
        raw.get("source") == "Ciqual"
        and isinstance(code, str)
        and ciqual.get(code) is not None
    )


def _quantity(grams: float) -> str:
    """Why a quantity is impossible ('' if it is not)."""
    return (
        "" if 0 < grams <= _MAX_GRAMS else f"quantité impossible ({grams:g} g)"
    )


def _implausible(grams: float, v: dict[str, float]) -> str:
    """Why these values cannot describe a real food ('' if they can)."""
    if _quantity(grams):
        return _quantity(grams)
    if any(value < 0 for value in v.values()):
        return "valeur négative"
    mass = v["protein_g"] + v["carbs_g"] + v["fat_g"] + v["fiber_g"]
    if mass > grams * 1.05:
        return "nutriments plus lourds que l'aliment"
    if v["sugars_g"] > v["carbs_g"] + 0.5 or v["sat_fat_g"] > v["fat_g"] + 0.5:
        return "sucres > glucides ou saturés > lipides"
    if v["sodium_mg"] > grams * _SODIUM_PER_G:
        return "sodium impossible"
    return ""


def _number(value: Any) -> float | None:
    """A number (French comma accepted), or None."""
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _texts(value: Any) -> list[str]:
    """A short list of short texts."""
    if not isinstance(value, list):
        return []
    return [meal_remarks.short(v) for v in value[:6] if str(v).strip()]
