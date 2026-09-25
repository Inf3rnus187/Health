"""Everything Open Food Facts says of a product beyond its 8 values.

Kept on the food's sheet (``product_info``) and given to the meal
reading: ingredients, allergens and traces, additives (E numbers),
Nutri-Score, NOVA group (1 unprocessed … 4 ultra-processed), the share
of fruits, vegetables and legumes, the traffic-light levels (fat,
saturated fat, sugars, salt), labels, categories, serving size, and
every other nutrient it gives per 100 g (in grams: potassium, vitamin
C…). Nothing is guessed: a field Open Food Facts leaves empty stays
empty.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas.food import ProductInfo

#: What the sheet's 8 values already hold, and what is not a nutrient.
_KNOWN = frozenset(
    "energy energy-kj energy-kcal proteins carbohydrates sugars fat "
    "saturated-fat fiber salt sodium alcohol nutrition-score-fr "
    "nutrition-score-uk nova-group carbon-footprint-from-known-ingredients "
    "carbon-footprint-from-meat-or-fish".split()
)
_FRUITS = (
    "fruits-vegetables-legumes_100g",
    "fruits-vegetables-nuts_100g",
    "fruits-vegetables-legumes-estimate-from-ingredients_100g",
    "fruits-vegetables-nuts-estimate-from-ingredients_100g",
)
FIELDS = (
    "ingredients_text_fr,ingredients_text,allergens_tags,traces_tags,"
    "additives_tags,nutriscore_grade,nutriscore_score,nova_group,"
    "nutrient_levels,labels,categories,serving_size"
)
_MOST_NUTRIENTS = 40


def info(product: dict[str, Any], barcode: str) -> dict[str, Any]:
    """The product's details, checked (a bad field is left out)."""
    found = {
        "ingredients": _text(
            product, "ingredients_text_fr", "ingredients_text"
        ),
        "allergens": _tags(product.get("allergens_tags")),
        "traces": _tags(product.get("traces_tags")),
        "additives": [t.upper() for t in _tags(product.get("additives_tags"))],
        "nutriscore": _grade(product.get("nutriscore_grade")),
        "nutriscore_score": product.get("nutriscore_score"),
        "nova": product.get("nova_group"),
        "fruits_veg_pct": _fruits(product.get("nutriments")),
        "levels": _levels(product.get("nutrient_levels")),
        "labels": _text(product, "labels")[:500],
        "categories": _text(product, "categories")[:500],
        "serving": _text(product, "serving_size")[:80],
        "other_100g": _others(product.get("nutriments")),
        "url": f"https://fr.openfoodfacts.org/produit/{barcode}",
    }
    return _checked(found)


def _checked(found: dict[str, Any]) -> dict[str, Any]:
    """Validated by the schema; a field that fails is dropped alone."""
    try:
        return ProductInfo.model_validate(found).model_dump()
    except ValidationError as exc:
        bad = {str(err["loc"][0]) for err in exc.errors() if err["loc"]}
        kept = {k: v for k, v in found.items() if k not in bad}
        return ProductInfo.model_validate(kept).model_dump()


def _text(product: dict[str, Any], *keys: str) -> str:
    """The first non-empty text among ``keys``."""
    for key in keys:
        value = product.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:4000]
    return ""


def _tags(raw: Any) -> list[str]:
    """« en:celery » → « celery » (the words the page shows)."""
    if not isinstance(raw, list):
        return []
    words = [str(t).split(":", 1)[-1].replace("-", " ") for t in raw]
    return [w for w in words if w][:60]


def _grade(raw: Any) -> str:
    """A Nutri-Score letter, or empty (« unknown », « not-applicable »)."""
    value = str(raw or "").strip().lower()
    return value if value in ("a", "b", "c", "d", "e") else ""


def _fruits(nutriments: Any) -> float | None:
    """The share of fruits, vegetables and legumes (%), given or estimated."""
    found = nutriments if isinstance(nutriments, dict) else {}
    for key in _FRUITS:
        value = found.get(key)
        if isinstance(value, int | float) and 0 <= value <= 100:  # noqa: PLR2004
            return round(float(value), 2)
    return None


def _levels(raw: Any) -> dict[str, str]:
    """Levels of fat, saturated-fat, sugars, salt: low, moderate, high."""
    if not isinstance(raw, dict):
        return {}
    return {
        str(k)[:40]: str(v)
        for k, v in raw.items()
        if v in ("low", "moderate", "high")
    }


def _others(nutriments: Any) -> dict[str, float]:
    """The other nutrients per 100 g (grams), the sheet's 8 left out."""
    found = nutriments if isinstance(nutriments, dict) else {}
    out: dict[str, float] = {}
    for key, value in found.items():
        name = str(key).removesuffix("_100g")
        if not str(key).endswith("_100g") or name in _KNOWN:
            continue
        if name.startswith("fruits-vegetables") or isinstance(value, bool):
            continue
        if isinstance(value, int | float) and value >= 0:
            out[name[:60]] = float(value)
    return dict(sorted(out.items())[:_MOST_NUTRIENTS])
