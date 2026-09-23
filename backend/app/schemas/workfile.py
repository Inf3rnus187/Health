"""Schemas of the work file: absences (sick leave) and evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

AbsenceKind = Literal[
    "arret_maladie",
    "accident_travail",
    "maladie_pro",
    "conge",
    "repos",
    "autre",
]


class AbsenceIn(BaseModel):
    """A period off work with its kind and cause."""

    start_date: date
    end_date: date
    kind: AbsenceKind = "arret_maladie"
    cause: str = Field(default="", max_length=4000)
    note: str = Field(default="", max_length=4000)
    #: am: from the morning (default); pm: from the afternoon.
    start_half: Literal["am", "pm"] = "am"
    #: pm: until the evening (default); am: until noon.
    end_half: Literal["am", "pm"] = "pm"

    @model_validator(mode="after")
    def _ordered(self) -> AbsenceIn:
        """The end cannot come before the start (half days included)."""
        if self.end_date < self.start_date:
            raise ValueError("end_date before start_date")
        same_day = self.end_date == self.start_date
        if same_day and (self.start_half, self.end_half) == ("pm", "am"):
            raise ValueError("an afternoon cannot end at noon the same day")
        return self


class AbsenceOut(AbsenceIn):
    """A stored absence (``days``: half days counted as ½)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    days: float


class EvidenceUpdate(BaseModel):
    """Fix an evidence item's details (only the fields given)."""

    occurred_at: datetime | None = None
    kind: str | None = Field(default=None, max_length=16)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    count: int | None = Field(default=None, ge=1, le=10000)
    absence_id: str | None = None
    ended_at: datetime | None = None
    place: str | None = Field(default=None, max_length=300)
    amount: float | None = Field(default=None, ge=0, le=100000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class EvidenceOut(BaseModel):
    """A stored evidence item (the file itself is fetched apart)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    occurred_at: datetime
    time_known: bool = True
    ended_at: datetime | None = None
    kind: str
    title: str
    description: str
    count: int
    place: str = ""
    amount: float | None = None
    currency: str = "EUR"
    meal_id: str | None = None
    file_name: str | None
    media_type: str | None
    size_bytes: int
    sha256: str | None
    absence_id: str | None
    created_at: datetime

    @field_validator("occurred_at", "ended_at", "created_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        """A time read back without offset (SQLite) is UTC."""
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)
