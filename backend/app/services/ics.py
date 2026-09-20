"""Minimal iCalendar (.ics) VEVENT parser — no external dependency.

Handles line unfolding and the common date-time value forms
(``YYYYMMDD``, ``YYYYMMDDTHHMMSS`` and ``…Z``); times are treated as UTC.
Recurring rules are not expanded — one row per VEVENT.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_KEYS = {"SUMMARY", "DTSTART", "DTEND", "LOCATION", "UID"}
_DATE_LEN = 8  # YYYYMMDD
_DT_LEN = 15  # YYYYMMDDTHHMMSS


def parse_events(text: str) -> list[dict[str, Any]]:
    """Return one dict per VEVENT with title/start/end/location/uid."""
    events: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            event = _event(current) if current is not None else None
            if event is not None:
                events.append(event)
            current = None
        elif current is not None:
            _absorb(current, line)
    return events


def _unfold(text: str) -> list[str]:
    """Join RFC-5545 folded continuation lines."""
    out: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line.rstrip())
    return out


def _absorb(current: dict[str, str], line: str) -> None:
    """Record a property line (name;params:value) we care about."""
    if ":" not in line:
        return
    name, _, value = line.partition(":")
    key = name.split(";")[0].upper()
    if key in _KEYS:
        current[key] = value


def _event(fields: dict[str, str]) -> dict[str, Any] | None:
    """Build an event dict, or ``None`` without a valid start."""
    start = _dt(fields.get("DTSTART", ""))
    if start is None:
        return None
    return {
        "title": (fields.get("SUMMARY") or "Rendez-vous")[:200],
        "starts_at": start,
        "ends_at": _dt(fields.get("DTEND", "")),
        "location": fields.get("LOCATION") or None,
        "uid": fields.get("UID") or None,
    }


def _dt(value: str) -> datetime | None:
    """Parse an iCalendar date or date-time to an aware UTC datetime."""
    v = value.strip()
    try:
        if len(v) == _DATE_LEN:
            return datetime(int(v[0:4]), int(v[4:6]), int(v[6:8]), tzinfo=UTC)
        if len(v) >= _DT_LEN and v[8] == "T":
            return datetime(
                int(v[0:4]),
                int(v[4:6]),
                int(v[6:8]),
                int(v[9:11]),
                int(v[11:13]),
                int(v[13:15]),
                tzinfo=UTC,
            )
    except (ValueError, IndexError):
        return None
    return None
