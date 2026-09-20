"""Parse Apple Health timestamp and numeric attribute strings.

``to_dt`` is called once per sample (millions of times on a full import),
so the common ``YYYY-MM-DD HH:MM:SS ±ZZZZ`` shape is parsed by hand — far
cheaper than ``strptime`` — with ``strptime``/ISO fallbacks for oddities.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

_FMT = "%Y-%m-%d %H:%M:%S %z"
_MIN_LEN = 25  # "YYYY-MM-DD HH:MM:SS ±ZZZZ"
_OFF_LEN = 5  # "±HHMM"


def to_dt(raw: str | None) -> datetime | None:
    """Parse ``YYYY-MM-DD HH:MM:SS ±ZZZZ`` into an aware datetime."""
    if not raw:
        return None
    fast = _fast(raw)
    return fast if fast is not None else _slow(raw)


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


def _fast(raw: str) -> datetime | None:
    """Hand-parse the canonical space-separated, offset-suffixed form."""
    if len(raw) < _MIN_LEN or raw[4] != "-" or raw[13] != ":":
        return None
    tz = _zone(raw[20:])
    if tz is None:
        return None
    try:
        return datetime(
            int(raw[0:4]),
            int(raw[5:7]),
            int(raw[8:10]),
            int(raw[11:13]),
            int(raw[14:16]),
            int(raw[17:19]),
            tzinfo=tz,
        )
    except ValueError:
        return None


def _zone(off: str) -> timezone | None:
    """Parse a ``±HHMM`` offset, or ``None`` if it is not one."""
    if len(off) < _OFF_LEN or off[0] not in "+-":
        return None
    try:
        delta = timedelta(hours=int(off[1:3]), minutes=int(off[3:5]))
    except ValueError:
        return None
    return timezone(delta if off[0] == "+" else -delta)


def _slow(raw: str) -> datetime | None:
    """Fallback: strptime, then ISO-8601 (``…T…Z`` / offset)."""
    try:
        return datetime.strptime(raw, _FMT)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
