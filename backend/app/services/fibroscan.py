"""Read the key numbers of a FibroScan (transient elastography) report.

Deterministic, like the lab parser: the median CAP (liver fat, dB/m),
the median stiffness E (fibrosis, kPa) and, when printed, the weight and
height measured that day — each only accepted inside its physical range
and dated with the EXAM date (never the patient's birth date).
"""

from __future__ import annotations

import re
from datetime import date

from app.services import doc_dates
from app.services import metabolic_catalog as cat

_CAP = re.compile(r"\bCAP\b[^\d\n]{0,40}?(\d{3})(?![\d.,])")
_LSM = re.compile(
    r"(?:\bE\s*=|\bE\s*m[ée]dian[e]?|[ÉE]lasticit[ée]|[Ss]tiffness|\bLSM\b"
    r"|\bE\s*\(kPa\))[^\d\n]{0,40}?(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:kPa)?"
)
_WEIGHT = re.compile(r"\b(?:Poids|Weight)\s*:\s*(\d{2,3}(?:[.,]\d)?)\s*kg")
_HEIGHT = re.compile(r"\b(?:Taille|Height)\s*:\s*(\d{3})\s*cm")

#: (metric key, pattern, lowest, highest) read from a FibroScan report.
_FIELDS = (
    (cat.CAP_KEY, _CAP, 100.0, 400.0),
    (cat.LSM_KEY, _LSM, 1.5, 75.0),
    ("body.weight", _WEIGHT, 30.0, 300.0),
    ("body.height", _HEIGHT, 120.0, 230.0),
)


def parse(text: str, fallback: date) -> list[tuple[str, float, date]]:
    """``(metric key, value, exam date)`` found in a FibroScan report."""
    if "FibroScan" not in text and "Fibroscan" not in text:
        if "kPa" not in text or "dB/m" not in text:
            return []
    day = exam_date(text) or fallback
    out: list[tuple[str, float, date]] = []
    for key, pattern, low, high in _FIELDS:
        value = _first(pattern, text, (low, high))
        if value is not None:
            out.append((key, value, day))
    has_liver = any(key in (cat.CAP_KEY, cat.LSM_KEY) for key, _, _ in out)
    return out if has_liver else []


def exam_date(text: str) -> date | None:
    """The exam date: the latest printed date that is not a birth date."""
    return doc_dates.latest(text)


def _first(
    pattern: re.Pattern[str], text: str, bounds: tuple[float, float]
) -> float | None:
    """First match of ``pattern`` whose number lies within ``bounds``."""
    for match in pattern.finditer(text):
        value = float(match.group(1).replace(",", "."))
        if bounds[0] <= value <= bounds[1]:
            return value
    return None
