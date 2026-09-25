"""Schema for the home-page headline tiles."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_validator


class TileOut(BaseModel):
    """One headline metric's latest value plus evolution stats."""

    key: str
    label: str
    unit: str | None
    value: float
    date_key: date
    at: datetime | None = None
    delta: float | None = None
    avg7: float | None = None
    spark: list[float] = Field(default_factory=list)

    @field_validator("at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        """Always send the instant with its UTC offset."""
        if value is None or value.tzinfo:
            return value
        return value.replace(tzinfo=UTC)
