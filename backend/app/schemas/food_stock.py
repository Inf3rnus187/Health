"""A food's stock: a move typed in, a move stored, the level now."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockIn(BaseModel):
    """A purchase, a loss or a count, of one food.

    The food: ``food_id``, else ``barcode`` (a pack scanned), else
    ``food`` (its name: accents and case ignored, the start of a word of
    3 letters or more is enough). The quantity: one of ``packs`` (×
    the package), ``units`` (× the unit: « 6 tomates ») or ``grams``;
    none for a purchase is one pack.
    """

    food_id: str | None = Field(default=None, max_length=36)
    barcode: str | None = Field(default=None, pattern=r"^\d{8,14}$")
    food: str | None = Field(default=None, min_length=1, max_length=200)
    kind: str = Field(default="purchase", pattern="^(purchase|out|count)$")
    packs: float | None = Field(default=None, ge=0, le=500)
    units: float | None = Field(default=None, ge=0, le=5000)
    grams: float | None = Field(default=None, ge=0, le=500000)
    at: datetime | None = None
    note: str = Field(default="", max_length=1000)


class StockMoveOut(BaseModel):
    """A stored move."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    food_id: str
    at: datetime
    kind: str
    grams: float
    said: str
    note: str
    source: str
    created_at: datetime

    @field_validator("at", "created_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        """Always send the instant with its UTC offset."""
        return value if value.tzinfo else value.replace(tzinfo=UTC)
