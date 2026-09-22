"""Accept an AI-extracted value only if the document proves it.

A language model can misread or invent numbers. A proposed value is kept
only when its metric is a known one, its unit is that metric's unit and
BOTH its number and its date are printed in the document text (OCR text
for scanned pages). Anything else is rejected, never stored.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, NamedTuple

_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y")


class Grounded(NamedTuple):
    """A value proven by the document text."""

    key: str
    value: float
    day: date


def ground(
    items: Any, text: str, units: dict[str, str]
) -> tuple[list[Grounded], int]:
    """Split proposed values into proven ones and a rejected count."""
    flat = " ".join(text.split())
    accepted: list[Grounded] = []
    rejected = 0
    for item in items if isinstance(items, list) else []:
        found = _check(item, flat, units)
        if found is None:
            rejected += 1
        else:
            accepted.append(found)
    return accepted, rejected


def date_in(day: date, text: str) -> bool:
    """Whether ``day`` is printed in ``text`` in a usual format."""
    flat = " ".join(text.split())
    return any(day.strftime(fmt) in flat for fmt in _DATE_FORMATS)


def _check(item: Any, text: str, units: dict[str, str]) -> Grounded | None:
    """One proposed value, if every part of it is proven."""
    if not isinstance(item, dict):
        return None
    key = str(item.get("key", ""))
    value = _number(item.get("value"))
    day = _day(item.get("date"))
    if key not in units or value is None or day is None:
        return None
    if _unit(item.get("unit")) != _unit(units[key]):
        return None
    if not (_printed(value, text) and date_in(day, text)):
        return None
    return Grounded(key, value, day)


def _printed(value: float, text: str) -> bool:
    """Whether the number appears as-is (comma or dot decimal)."""
    forms = {f"{value:g}", f"{value:.1f}", f"{value:.2f}"}
    forms |= {form.replace(".", ",") for form in forms}
    return any(
        re.search(rf"(?<![\d.,]){re.escape(form)}(?![\d])", text)
        for form in forms
    )


def _number(value: Any) -> float | None:
    """A finite number from the model's answer."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _day(value: Any) -> date | None:
    """An ISO ``YYYY-MM-DD`` date from the model's answer."""
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _unit(value: Any) -> str:
    """Comparable unit spelling (case, spaces, micro sign)."""
    text = str(value or "").strip().lower().replace(" ", "")
    return text.replace("µ", "u").replace("μ", "u")
