"""French formatting of numbers and dates in the clinical facts."""

from __future__ import annotations

from datetime import date

Line = tuple[str, str]


def num(value: float, digits: int = 2) -> str:
    """French number (decimal comma, no trailing zeros)."""
    return f"{round(value, digits):g}".replace(".", ",")


def day(value: date | str | None) -> str:
    """``dd/mm/yyyy`` of an ISO date or a date."""
    if value is None:
        return "date inconnue"
    text = value.isoformat() if isinstance(value, date) else str(value)
    return f"{text[8:10]}/{text[5:7]}/{text[:4]}"
