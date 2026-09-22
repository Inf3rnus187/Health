"""Accept an AI-extracted value only if the document proves it.

A language model can misread or invent numbers. A proposed value is kept
only when its metric is a known one, its unit is that metric's unit and
BOTH its number and its date are printed in the document text (OCR text
for scanned pages). Anything else is rejected — with the reason, shown
to the user — and never stored.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, NamedTuple

from app.services import doc_dates

_MAX_REJECTED = 30


class Grounded(NamedTuple):
    """A value proven by the document text."""

    key: str
    value: float
    day: date


def ground(
    items: Any, text: str, units: dict[str, str]
) -> tuple[list[Grounded], list[dict[str, Any]]]:
    """Split proposed values into proven ones and rejections (+ reason)."""
    flat = " ".join(text.split())
    accepted: list[Grounded] = []
    rejected: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        found, reason = _check(item, flat, units)
        if found is not None:
            accepted.append(found)
        elif len(rejected) < _MAX_REJECTED:
            rejected.append(_rejection(item, reason))
    return accepted, rejected


def date_in(day: date, text: str) -> bool:
    """Whether ``day`` is printed in ``text`` in a usual format."""
    return doc_dates.printed(day, text)


def _check(
    item: Any, text: str, units: dict[str, str]
) -> tuple[Grounded | None, str]:
    """One proposed value, if every part of it is proven."""
    if not isinstance(item, dict):
        return None, "format invalide"
    key = str(item.get("key", ""))
    value = _number(item.get("value"))
    day = _day(item.get("date"))
    if value is None or day is None:
        return None, "valeur ou date illisible"
    reason = _problem(key, value, day, item.get("unit"), text, units)
    return (None, reason) if reason else (Grounded(key, value, day), "")


def _problem(
    key: str,
    value: float,
    day: date,
    unit: Any,
    text: str,
    units: dict[str, str],
) -> str:
    """Why a proposal is not proven by the document ('' when it is)."""
    if key not in units:
        return "mesure inconnue"
    if _unit(unit) != _unit(units[key]):
        return f"unité différente (attendu {units[key] or 'aucune'})"
    if not _printed(value, text):
        return "nombre absent du document"
    if not doc_dates.printed(day, text):
        return "date absente du document"
    return ""


def _rejection(item: Any, reason: str) -> dict[str, Any]:
    """A rejected proposal as shown to the user."""
    data = item if isinstance(item, dict) else {"value": str(item)[:40]}
    return {
        "key": str(data.get("key", ""))[:40],
        "value": str(data.get("value", ""))[:20],
        "unit": str(data.get("unit", ""))[:15],
        "date": str(data.get("date", ""))[:10],
        "reason": reason,
    }


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
