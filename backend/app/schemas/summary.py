"""Schema for the home-page headline tiles."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class TileOut(BaseModel):
    """One headline metric's latest value."""

    key: str
    label: str
    unit: str | None
    value: float
    date_key: date
    at: datetime | None = None
