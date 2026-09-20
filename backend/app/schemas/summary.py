"""Schema for the home-page headline tiles."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


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
