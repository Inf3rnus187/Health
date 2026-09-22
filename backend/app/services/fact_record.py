"""Facts from the record: profile, conditions, treatments, documents."""

from __future__ import annotations

from typing import Any

from app.models.medical import Condition, MedicalDocument, Treatment
from app.services import metabolic_catalog
from app.services.fact_format import Line, day, num

_STATUS = {"active": "active", "resolved": "résolue", "suspected": "suspectée"}


def profile(found: dict[str, Any]) -> list[Line]:
    """Age and height."""
    out: list[Line] = []
    if found.get("birth_year"):
        age = metabolic_catalog.age(found["birth_year"])
        out.append(("Profil", f"Âge : {num(age, 0)} ans"))
    if found.get("height_cm"):
        out.append(("Profil", f"Taille : {num(found['height_cm'], 0)} cm"))
    return out


def conditions(items: list[Condition]) -> list[Line]:
    """Declared conditions with their status and onset."""
    out: list[Line] = []
    for cond in items:
        state = _STATUS.get(cond.status, cond.status)
        if cond.onset_date:
            state += f", depuis le {day(cond.onset_date)}"
        out.append(("Maladies déclarées", f"{cond.name} ({state})"))
    return out


def treatments(items: list[Treatment]) -> list[Line]:
    """Declared treatments, current or stopped."""
    out: list[Line] = []
    for item in items:
        desc = " · ".join(p for p in (item.dose, item.frequency) if p)
        state = "en cours" if item.active else "arrêté"
        if item.start_date:
            state += f", début le {day(item.start_date)}"
        if item.end_date:
            state += f", arrêt le {day(item.end_date)}"
        name = f"{item.name} ({desc})" if desc else item.name
        out.append(("Traitements", f"{name} — {state}"))
    return out


def documents(items: list[MedicalDocument]) -> list[Line]:
    """The record's documents (title, type, date, verified values)."""
    out: list[Line] = []
    for doc in items:
        values = len((doc.analysis or {}).get("values") or [])
        when = day(doc.doc_date or doc.created_at.date())
        text = f"{doc.title} ({doc.kind}, {when})"
        if values:
            text += f", {values} valeurs vérifiées"
        out.append(("Documents du dossier", text))
    return out
