"""What a meal form sends besides its text: foods eaten, reading delay."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.core.config import get_settings
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


def delay(text: str) -> timedelta | None:
    """How long to put a meal's reading off (None: read at once).

    Minutes, ``2`` or ``2.5`` (``2,5`` too); empty or 0: at once.
    """
    if not text.strip():
        return None
    try:
        minutes = float(text.strip().replace(",", "."))
    except ValueError as exc:
        raise InvalidInputError("analysis_delay_min: minutes, e.g. 2") from exc
    most = get_settings().meal_analysis_max_delay_min
    if not 0 <= minutes <= most:
        raise InvalidInputError(
            f"analysis_delay_min: between 0 and {most:g} minutes"
        )
    return timedelta(minutes=minutes) if minutes else None
