"""Parse Apple Health timestamp and numeric attribute strings."""

from __future__ import annotations

from datetime import date, datetime

_FMT = "%Y-%m-%d %H:%M:%S %z"


def to_dt(raw: str | None) -> datetime | None:
    """Parse ``YYYY-MM-DD HH:MM:SS ±ZZZZ`` into an aware datetime."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, _FMT)
    except ValueError:
        return _iso(raw)


def _iso(raw: str) -> datetime | None:
    """Fallback: parse an ISO-8601 timestamp (``…T…Z`` or offset)."""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_day(raw: str | None) -> date | None:
    """Read the calendar day from a timestamp attribute."""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def to_float(raw: str | None) -> float | None:
    """Parse a numeric attribute, tolerating missing or bad values."""
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
