"""A trace read from a file, before it is stored (see :mod:`trace_store`)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import NamedTuple
from zoneinfo import ZoneInfo

#: The time given to a trace known only by its date.
NOON = time(12, 0)


class Trace(NamedTuple):
    """One trace read from a file (times in UTC)."""

    start: datetime
    end: datetime | None
    time_known: bool
    kind: str
    place: str
    vendor: str
    amount: float | None
    currency: str
    what: str
    group: str
    #: (file name, media type, bytes) — a receipt is its own proof.
    file: tuple[str, str, bytes] | None = None
    #: How many actions (a day of tickets: 12 comments).
    actions: int = 1
    #: One trace a day per source (tickets, a chat): met again, the day
    #: is replaced when the new one holds more actions.
    daily: bool = False


def noon(day: date, tz: ZoneInfo) -> datetime:
    """A day known without its time: local noon, in UTC."""
    return datetime.combine(day, NOON, tzinfo=tz).astimezone(UTC)
