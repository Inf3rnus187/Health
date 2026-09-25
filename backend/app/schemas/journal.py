"""Schemas of the journal: urinations and meals."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from app.schemas.food import FoodPortion
from app.services import meal_reference


class UrinationIn(BaseModel):
    """One urination (now when ``at`` is omitted)."""

    at: datetime | None = None


class MealUpdate(BaseModel):
    """Change a meal's type, time or description (then re-read)."""

    meal_type: str | None = None
    eaten_at: datetime | None = None
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, ge=0, le=10000)
    vendor: str | None = Field(default=None, max_length=120)
    #: The catalogue foods eaten (replaces the list; [] removes them).
    foods: list[FoodPortion] | None = Field(default=None, max_length=20)


class MealOut(BaseModel):
    """A meal with its reading (items, nutrients, assessment)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    eaten_at: datetime
    date_key: date
    meal_type: str
    description: str
    price: float | None = None
    vendor: str = ""
    has_photo: bool = False
    #: The other photos (the pack, its label…): GET /meals/{id}/photos/{id}.
    photo_ids: list[str] = []
    foods: list[dict[str, Any]] = []
    analysis_status: str | None = None
    analysis: dict[str, Any] | None = None
    created_at: datetime

    @field_validator("eaten_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        """Always send the instant with its UTC offset."""
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reference(self) -> dict[str, Any] | None:
        """The totals against official daily references, by meal type.

        Each nutrient's share of an adult-type day and the meal type's
        indicative part of it (``GET /nutrition/references``).
        """
        return meal_reference.compare(self.analysis, self.meal_type)
