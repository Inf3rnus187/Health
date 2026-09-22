"""Exact values of a document and how they are shown / summarised."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.models.medical import MedicalDocument
from app.services import biology, doc_dates, document_prompt, fibroscan
from app.services import document_grounding as grounding
from app.services.biology import Reading

#: Labels and units of the body values a FibroScan report prints.
_BODY = {
    "body.weight": ("Poids", "kg"),
    "body.height": ("Taille", "cm"),
}


def document_day(doc: MedicalDocument, text: str) -> date:
    """The document's date: given, printed (never a birth date), upload."""
    return (
        doc.doc_date
        or biology.sample_date(text)
        or doc_dates.latest(text)
        or doc.created_at.date()
    )


def exact(text: str, kind: str, day: date) -> list[Reading]:
    """Values read by the exact parsers (lab report, FibroScan)."""
    lab_day = biology.sample_date(text)
    out: list[Reading] = []
    if lab_day is not None or kind == "biologie":
        out.extend(biology.parse_text(text, lab_day or day))
    labels = {**document_prompt.LIVER, **_BODY}
    for key, value, when in fibroscan.parse(text, day):
        label, unit = labels[key]
        out.append(Reading(key, label, unit, when, value))
    return out


def new_readings(
    proven: list[grounding.Grounded], found: list[Reading]
) -> list[Reading]:
    """Proven AI values the exact parsers did not already find."""
    known = {(r.key, r.day) for r in found}
    labels = document_prompt.allowed()
    out: list[Reading] = []
    for item in proven:
        if (item.key, item.day) not in known:
            label, unit = labels[item.key]
            out.append(Reading(item.key, label, unit, item.day, item.value))
            known.add((item.key, item.day))
    return out


def fact(reading: Reading) -> str:
    """A verified value as given to the summary model."""
    value = f"{reading.value:g}".replace(".", ",")
    unit = f" {reading.unit}" if reading.unit else ""
    return f"{reading.label} : {value}{unit} ({reading.day:%d/%m/%Y})"


def row(reading: Reading, origin: str) -> dict[str, Any]:
    """One recorded value, as shown under the document."""
    return {
        "key": reading.key,
        "label": reading.label,
        "value": reading.value,
        "unit": reading.unit,
        "date": reading.day.isoformat(),
        "origin": origin,
    }
