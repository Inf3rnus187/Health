"""Schemas of the journal: urinations and meals."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UrinationIn(BaseModel):
    """One urination (now when ``at`` is omitted)."""

    at: datetime | None = None


class MealUpdate(BaseModel):
    """Change a meal's type, time or description (then re-read)."""

    meal_type: str | None = None
    eaten_at: datetime | None = None
    description: str | None = Field(default=None, max_length=2000)


class MealOut(BaseModel):
    """A meal with its reading (items, nutrients, assessment)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    eaten_at: datetime
    date_key: date
    meal_type: str
    description: str
    has_photo: bool = False
    analysis_status: str | None = None
    analysis: dict[str, Any] | None = None
    created_at: datetime

    @field_validator("eaten_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        """Always send the instant with its UTC offset."""
        return value if value.tzinfo else value.replace(tzinfo=UTC)
