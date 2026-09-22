"""Conditions and treatments read in documents but not declared yet.

Offered in the Dossier and Suivi pages, never added silently. Each
suggestion lists the documents that mention it.
"""

from __future__ import annotations

from typing import Any

from app.models.medical import Condition, MedicalDocument, Treatment
from app.services.textfold import fold, same_name


def doc_ref(doc: MedicalDocument) -> dict[str, Any]:
    """A short reference to a document (id, title, date, kind)."""
    day = doc.doc_date or doc.created_at.date()
    return {
        "id": doc.id,
        "title": doc.title,
        "date": day.isoformat(),
        "kind": doc.kind,
    }


def conditions(
    docs: list[MedicalDocument], declared: list[Condition]
) -> list[dict[str, Any]]:
    """Diagnoses read in documents that are not declared yet."""
    found: dict[str, dict[str, Any]] = {}
    for doc in docs:
        for name in _analysis(doc).get("conditions") or []:
            if any(same_name(name, c.name) for c in declared):
                continue
            _add(found, {"name": str(name)}, doc)
    return list(found.values())


def treatments(
    docs: list[MedicalDocument], declared: list[Treatment]
) -> list[dict[str, Any]]:
    """Medications read in documents (prescriptions first) not declared."""
    found: dict[str, dict[str, Any]] = {}
    for doc in sorted(docs, key=lambda d: d.kind != "ordonnance"):
        for med in _analysis(doc).get("medications") or []:
            name = str(med.get("name") or "")
            if not name or any(_same_drug(name, t.name) for t in declared):
                continue
            _add(found, {**med, "name": name}, doc)
    return list(found.values())


def _add(
    found: dict[str, dict[str, Any]], item: dict[str, Any], doc: MedicalDocument
) -> None:
    """Merge one mention into the suggestions (one per folded name)."""
    key = next((k for k in found if same_name(k, item["name"])), None)
    if key is None:
        found[fold(item["name"])] = {**item, "documents": [doc_ref(doc)]}
    elif all(ref["id"] != doc.id for ref in found[key]["documents"]):
        found[key]["documents"].append(doc_ref(doc))


def _same_drug(left: str, right: str) -> bool:
    """Same medication: same first word (the molecule / brand)."""
    a, b = fold(left).split(), fold(right).split()
    return bool(a and b) and (a[0] == b[0] or same_name(left, right))


def _analysis(doc: MedicalDocument) -> dict[str, Any]:
    """The document's finished AI reading (empty when none)."""
    if doc.analysis_status != "done" or not doc.analysis:
        return {}
    return doc.analysis
