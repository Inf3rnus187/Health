"""The record's chronology, newest first.

Documents, appointments, diagnoses and treatment starts / stops on one
dated list.
"""

from __future__ import annotations

from typing import Any

from app.models.medical import (
    Appointment,
    Condition,
    MedicalDocument,
    Treatment,
)
from app.services.record_suggest import doc_ref


def timeline(
    docs: list[MedicalDocument],
    conditions: list[Condition],
    treatments: list[Treatment],
    appointments: list[Appointment],
) -> list[dict[str, Any]]:
    """Every dated event of the record, newest first."""
    items = [_document(doc) for doc in docs]
    items += [
        _item(c.onset_date.isoformat(), "condition", c.name, c.status, c.id)
        for c in conditions
        if c.onset_date
    ]
    for t in treatments:
        items += _treatment(t)
    items += [
        _item(
            a.starts_at.date().isoformat(),
            "appointment",
            a.title,
            a.practitioner or a.location,
            a.id,
        )
        for a in appointments
    ]
    return sorted(items, key=lambda item: item["date"], reverse=True)


def _document(doc: MedicalDocument) -> dict[str, Any]:
    """A document on the timeline, with its AI summary when read."""
    ref = doc_ref(doc)
    analysis = doc.analysis if doc.analysis_status == "done" else None
    summary = (analysis or {}).get("summary")
    return _item(ref["date"], "document", doc.title, summary, doc.id, doc.kind)


def _treatment(t: Treatment) -> list[dict[str, Any]]:
    """A treatment's start and stop events."""
    dose = " · ".join(p for p in (t.dose, t.frequency) if p) or None
    out = []
    if t.start_date:
        out.append(
            _item(
                t.start_date.isoformat(), "treatment_start", t.name, dose, t.id
            )
        )
    if t.end_date:
        out.append(
            _item(t.end_date.isoformat(), "treatment_stop", t.name, dose, t.id)
        )
    return out


def _item(
    day: str,
    kind: str,
    title: str,
    detail: str | None,
    ref: str,
    sub: str | None = None,
) -> dict[str, Any]:
    """One timeline entry."""
    return {
        "date": day,
        "type": kind,
        "title": title,
        "detail": detail,
        "id": ref,
        "kind": sub,
    }
