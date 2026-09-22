"""Dates printed in medical documents (French, ISO and US formats).

Reports mix formats: a French lab writes ``16/09/2026``, an English
FibroScan page ``09/16/2026`` (month first), systems ``2026-09-16``.
``dd/mm`` is tried first (French documents), then ``mm/dd`` when the
first reading is impossible. A date written right after a birth label
(``Date of Birth``, ``né le``…) is a birth date, never an exam date.
"""

from __future__ import annotations

import re
from datetime import date

_NUMERIC = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_BIRTH = re.compile(
    r"(naissance|n[ée]e?\s+le|birth|\bDOB\b|\bDDN\b)[^\d\n]{0,25}$",
    re.IGNORECASE,
)
_FORMATS = ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d")


def found(text: str) -> list[date]:
    """Every valid non-birth date printed in ``text``."""
    out: list[date] = []
    for match in _NUMERIC.finditer(text):
        if _is_birth(text, match.start()):
            continue
        day = _day_month(*(int(g) for g in match.groups()))
        if day is not None:
            out.append(day)
    for match in _ISO.finditer(text):
        day = _safe(*(int(g) for g in match.groups()))
        if day is not None and not _is_birth(text, match.start()):
            out.append(day)
    return out


def latest(text: str) -> date | None:
    """The most recent non-birth date, not in the future."""
    today = date.today()
    days = [d for d in found(text) if d <= today]
    return max(days) if days else None


def printed(day: date, text: str) -> bool:
    """Whether ``day`` appears in ``text`` in a usual format."""
    flat = " ".join(text.split())
    return any(day.strftime(fmt) in flat for fmt in _FORMATS)


def _is_birth(text: str, start: int) -> bool:
    """Whether the date starting at ``start`` follows a birth label."""
    return bool(_BIRTH.search(text[max(0, start - 40) : start]))


def _day_month(first: int, second: int, year: int) -> date | None:
    """``dd/mm/yyyy`` first; ``mm/dd/yyyy`` only if the former is invalid."""
    return _safe(year, second, first) or _safe(year, first, second)


def _safe(year: int, month: int, day: int) -> date | None:
    """A date, or None when the numbers are not a calendar date."""
    try:
        return date(year, month, day)
    except ValueError:
        return None
