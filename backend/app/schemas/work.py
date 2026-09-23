"""Schemas of the work-hours log (clock-in / clock-out)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

#: Where the work was done.
Place = Literal["site", "remote"]


class ClockIn(BaseModel):
    """Clock in or out (now when ``at`` is omitted).

    ``place``: a clock-in on site or remote (a clock-out closes the
    session open, wherever it is).
    """

    kind: Literal["in", "out"]
    at: datetime | None = None
    place: Place = "site"


class WorkSessionIn(BaseModel):
    """A stretch at work typed by hand (one of the two times may be empty)."""

    start_at: datetime | None = None
    end_at: datetime | None = None
    note: str = Field(default="", max_length=200)
    #: remote: worked from home (even on a day already worked on site).
    place: Place = "site"


class WorkSessionUpdate(BaseModel):
    """Fix a session's times or note (only the fields given)."""

    start_at: datetime | None = None
    end_at: datetime | None = None
    note: str | None = Field(default=None, max_length=200)
    place: Place | None = None


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
    #: site or remote.
    place: str = "site"


class MergeIn(BaseModel):
    """The other session to make one with (it is deleted).

    ``start_at`` / ``end_at``: the times just typed for this session (in
    its editor), kept in the union instead of the stored ones.
    """

    other_id: str = Field(min_length=1, max_length=64)
    start_at: datetime | None = None
    end_at: datetime | None = None
