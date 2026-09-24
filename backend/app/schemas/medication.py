"""Schemas of medication intakes (a dose taken, or not)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_STATUS = ("taken", "skipped")


class IntakeIn(BaseModel):
    """A dose of a treatment: now or at ``taken_at`` (local if no offset)."""

    taken_at: datetime | None = None
    status: str = Field(default="taken", pattern="^(taken|skipped)$")
    dose: str | None = Field(default=None, max_length=80)
    note: str = Field(default="", max_length=1000)


class TakeIn(IntakeIn):
    """A dose by the treatment's name (an iPhone Shortcut's menu)."""

    treatment: str = Field(min_length=1, max_length=200)


class IntakeOut(BaseModel):
    """A recorded dose, with when it was entered and how."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    treatment_id: str | None
    name: str
    dose: str
    taken_at: datetime
    date_key: date
    status: str
    source: str
    note: str
    #: When it was entered (the proof it was not typed afterwards).
    created_at: datetime

    @field_validator("taken_at", "created_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        """Always send the instant with its UTC offset."""
        return value if value.tzinfo else value.replace(tzinfo=UTC)
