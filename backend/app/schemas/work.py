"""Schemas of the work-hours log (clock-in / clock-out)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ClockIn(BaseModel):
    """Clock in or out (now when ``at`` is omitted)."""

    kind: Literal["in", "out"]
    at: datetime | None = None


class WorkSessionIn(BaseModel):
    """A stretch at work typed by hand (one of the two times may be empty)."""

    start_at: datetime | None = None
    end_at: datetime | None = None
    note: str = Field(default="", max_length=200)


class WorkSessionUpdate(BaseModel):
    """Fix a session's times or note (only the fields given)."""

    start_at: datetime | None = None
    end_at: datetime | None = None
    note: str | None = Field(default=None, max_length=200)


class WorkSessionOut(BaseModel):
    """One session with its local day and duration."""

    id: str
    date_key: date
    start_at: datetime | None
    end_at: datetime | None
    hours: float | None
    #: complete, open (at work now), missing_start or missing_end.
    status: str
    source: str
    note: str
