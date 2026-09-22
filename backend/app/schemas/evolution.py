"""Request schema for the long-term evolution (profile form)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    """Profile and FibroScan values entered in the web form (optional)."""

    waist_cm: float | None = Field(default=None, ge=40, le=250)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    cap_db_m: float | None = Field(default=None, ge=100, le=400)
    lsm_kpa: float | None = Field(default=None, ge=1.5, le=75)
    date_key: date | None = None
