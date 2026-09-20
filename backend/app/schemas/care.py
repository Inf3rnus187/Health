"""Schemas for conditions, treatments and appointments."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_STATUS = frozenset({"active", "resolved", "suspected"})


class ConditionIn(BaseModel):
    """Create/replace a declared condition."""

    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=32)
    status: str = "active"
    onset_date: date | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def _known_status(cls, value: str) -> str:
        """Coerce an unknown status to ``active``."""
        return value if value in _STATUS else "active"


class ConditionOut(ConditionIn):
    """A condition with its identity and timestamp."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class TreatmentIn(BaseModel):
    """Create/replace a treatment."""

    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=80)
    frequency: str | None = Field(default=None, max_length=80)
    start_date: date | None = None
    end_date: date | None = None
    active: bool = True
    notes: str | None = None


class TreatmentOut(TreatmentIn):
    """A treatment with its identity and timestamp."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class AppointmentIn(BaseModel):
    """Create/replace an appointment."""

    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    ends_at: datetime | None = None
    practitioner: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class AppointmentOut(AppointmentIn):
    """An appointment with its identity, source and timestamp."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    created_at: datetime
