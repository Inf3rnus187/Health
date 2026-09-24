"""What a meal form sends besides its text: the catalogue foods eaten."""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.core.errors import InvalidInputError
from app.schemas.food import FoodPortion

_PORTIONS = TypeAdapter(list[FoodPortion])
MOST_FOODS = 20


def portions(text: str) -> list[dict[str, Any]] | None:
    """``[{"food_id", "grams"}]`` from a form field (None: not sent)."""
    if not text.strip():
        return None
    try:
        found = _PORTIONS.validate_python(json.loads(text))
    except (ValueError, ValidationError) as exc:
        raise InvalidInputError(
            'foods must be JSON: [{"food_id": "…", "grams": 125}]'
        ) from exc
    if len(found) > MOST_FOODS:
        raise InvalidInputError(f"At most {MOST_FOODS} foods")
    return [p.model_dump() for p in found]
