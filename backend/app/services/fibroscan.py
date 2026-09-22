"""Read the key numbers of a FibroScan (transient elastography) report.

Deterministic, like the lab parser: the median CAP (liver fat, dB/m)
and the median stiffness E (fibrosis, kPa), each only accepted inside
its physical range, dated with the exam date printed on the report.
"""

from __future__ import annotations

import re
from datetime import date

from app.services import metabolic_catalog as cat

_CAP = re.compile(r"\bCAP\b[^\d\n]{0,40}?(\d{3})(?![\d.,])")
_LSM = re.compile(
    r"(?:\bE\s*m[ée]dian[e]?|[ÉE]lasticit[ée]|[Ss]tiffness|\bLSM\b|"
    r"\bE\s*\(kPa\))[^\d\n]{0,40}?(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:kPa)?"
)
_DATE = re.compile(r"\b(\d{2})[/.-](\d{2})[/.-](\d{4})\b")
_CAP_RANGE = (100.0, 400.0)
_LSM_RANGE = (1.5, 75.0)


def parse(text: str, fallback: date) -> list[tuple[str, float, date]]:
    """``(metric key, value, exam date)`` found in a FibroScan report."""
    if "kPa" not in text and "dB/m" not in text:
        return []
    day = exam_date(text) or fallback
    out: list[tuple[str, float, date]] = []
    cap = _first(_CAP, text, _CAP_RANGE)
    if cap is not None:
        out.append((cat.CAP_KEY, cap, day))
    lsm = _first(_LSM, text, _LSM_RANGE)
    if lsm is not None:
        out.append((cat.LSM_KEY, lsm, day))
    return out


def exam_date(text: str) -> date | None:
    """First valid ``dd/mm/yyyy`` date printed in the report."""
    for match in _DATE.finditer(text):
        day, month, year = (int(g) for g in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def _first(
    pattern: re.Pattern[str], text: str, bounds: tuple[float, float]
) -> float | None:
    """First match of ``pattern`` whose number lies within ``bounds``."""
    for match in pattern.finditer(text):
        value = float(match.group(1).replace(",", "."))
        if bounds[0] <= value <= bounds[1]:
            return value
    return None
