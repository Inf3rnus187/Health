"""Request schema for the long-term evolution (profile form)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    """Anthropometric inputs entered in the web form (all optional)."""

    waist_cm: float | None = Field(default=None, ge=40, le=250)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    date_key: date | None = None
