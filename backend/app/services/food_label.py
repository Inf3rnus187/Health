"""Read a nutrition label photo with the vision model: a proposal.

The answer only pre-fills the food's form (name, brand, net weight,
values per 100 g); the user checks it and saves. Numbers are kept only
when plausible (the schema's bounds); « 12,5 g » and « < 0,5 g » read.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from pydantic import ValidationError

from app.core import ollama
from app.core.errors import InvalidInputError
from app.schemas.food import Per100g
from app.services import imaging

_PROMPT = """Tu lis l'emballage d'un produit alimentaire et son tableau \
de valeurs nutritionnelles. Relève exactement ce qui est imprimé, pour \
100 g (ou 100 ml), sans rien inventer ; une valeur absente vaut null.
Réponds uniquement en JSON :
{"name": "nom du produit", "brand": "marque", "net_g": 0, \
"per_100g": {"energy_kcal": 0, "protein_g": 0, "carbs_g": 0, \
"sugars_g": 0, "fat_g": 0, "sat_fat_g": 0, "fiber_g": 0, "salt_g": 0, \
"sodium_mg": 0}}"""
_TIME_LIMIT = 100.0
_SIDE = 2048


async def read(data: bytes) -> dict[str, Any]:
    """What the label says: name, brand, net weight, values per 100 g."""
    try:
        image = imaging.normalize_bytes(data, _SIDE)
    except Exception as exc:  # noqa: BLE001 - any decoding failure
        raise InvalidInputError("Unreadable image") from exc
    try:
        answer = await asyncio.wait_for(
            ollama.vision_json(_PROMPT, image), _TIME_LIMIT
        )
    except TimeoutError as exc:
        raise InvalidInputError("Lecture trop longue : réessayer") from exc
    return {
        "name": str(answer.get("name") or "")[:200],
        "brand": str(answer.get("brand") or "")[:120],
        "package_g": _grams(answer.get("net_g")),
        "per_100g": _values(answer.get("per_100g")),
    }


def _values(raw: Any) -> dict[str, float]:
    """The plausible values per 100 g (sodium from salt when absent)."""
    found = raw if isinstance(raw, dict) else {}
    values = {k: _number(v) for k, v in found.items()}
    salt = values.pop("salt_g", None)
    if values.get("sodium_mg") is None and salt is not None:
        values["sodium_mg"] = round(salt * 400, 1)  # 1 g salt = 400 mg Na
    kept = {k: v for k, v in values.items() if v is not None}
    try:
        checked = Per100g.model_validate(kept)
    except ValidationError:
        checked = Per100g.model_validate(_each(kept))
    return {k: v for k, v in checked.model_dump().items() if v is not None}


def _each(values: dict[str, float]) -> dict[str, float]:
    """Only the values that pass on their own."""
    out: dict[str, float] = {}
    for key, value in values.items():
        try:
            Per100g.model_validate({key: value})
        except ValidationError:
            continue
        out[key] = value
    return out


def _grams(raw: Any) -> float | None:
    """A net weight in grams, when plausible."""
    value = _number(raw)
    return value if value is not None and 0 < value <= 10000 else None  # noqa: PLR2004


def _number(raw: Any) -> float | None:
    """« 12,5 », « < 0,5 g », 3 → a number (None when none)."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    match = re.search(r"\d+(?:[.,]\d+)?", str(raw or ""))
    return float(match.group().replace(",", ".")) if match else None
