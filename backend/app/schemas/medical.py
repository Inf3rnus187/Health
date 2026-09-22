"""Schemas for medical documents."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

#: Accepted document kinds (French care context).
KINDS: frozenset[str] = frozenset(
    {
        "ordonnance",
        "imagerie",
        "compte_rendu",
        "biologie",
        "efr",
        "test_marche",
        "cda",
        "vaccination",
        "autre",
    }
)


class MedicalDocOut(BaseModel):
    """Public projection of a medical document (metadata only)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    title: str
    doc_date: date | None
    media_type: str
    size_bytes: int
    notes: str | None
    created_at: datetime
    analysis_status: str | None = None
    analysis: dict[str, Any] | None = None


def normalize_kind(kind: str) -> str:
    """Return a valid kind, defaulting unknown values to ``autre``."""
    cleaned = kind.strip().lower()
    return cleaned if cleaned in KINDS else "autre"


def parse_day(value: str | None) -> date | None:
    """Parse an optional ISO date from a form field, tolerating blanks."""
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
