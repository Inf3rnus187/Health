"""The medical record (dossier) built from everything the hub holds.

Documents with their AI reading, declared conditions and treatments plus
the ones the documents mention (suggestions to confirm), lab / imaging
results with the document each value came from, and one chronology.
The Suivi page links each condition to its indicators and documents.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.medical import Condition, MedicalDocument
from app.services import (
    appointments,
    conditions,
    medical,
    metric_overview,
    record_results,
    record_suggest,
    record_timeline,
    treatments,
)
from app.services.condition_links import indicators_for
from app.services.textfold import fold

#: Lab / imaging results are sparse: their whole history is shown.
_LAB = ("bio.", "liver.")
_LAB_DAYS = 36500


async def record(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """The whole record of one user."""
    docs = await medical.list_documents(session, user_id)
    conds = await conditions.list_all(session, user_id)
    treats = await treatments.list_all(session, user_id)
    appts = await appointments.list_all(session, user_id)
    origin = record_results.origins(docs)
    return {
        "documents": [_document(doc) for doc in docs],
        "suggested_conditions": record_suggest.conditions(docs, conds),
        "suggested_treatments": record_suggest.treatments(docs, treats),
        "results": await record_results.results(session, user_id, origin),
        "timeline": record_timeline.timeline(docs, conds, treats, appts),
    }


async def care(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    """Each declared condition with its indicators and documents."""
    docs = await medical.list_documents(session, user_id)
    out = []
    for cond in await conditions.list_all(session, user_id):
        indicators = [
            found
            for key in indicators_for(cond.name)
            if (found := await _indicator(session, user_id, key)) is not None
        ]
        out.append(
            {
                "id": cond.id,
                "name": cond.name,
                "status": cond.status,
                "indicators": indicators,
                "documents": _mentioning(cond, docs),
            }
        )
    return out


async def _indicator(
    session: AsyncSession, user_id: str, key: str
) -> dict[str, Any] | None:
    """The metric overview of one indicator (None without any value)."""
    days = _LAB_DAYS if key.startswith(_LAB) else 365
    try:
        found = await metric_overview.overview(session, user_id, key, days)
    except (NotFoundError, NoResultFound):
        return None
    return found if found.get("latest") else None


def _mentioning(
    cond: Condition, docs: list[MedicalDocument]
) -> list[dict[str, Any]]:
    """Documents whose reading mentions the condition."""
    name = fold(cond.name)
    return [
        record_suggest.doc_ref(doc)
        for doc in docs
        if name and name in fold(_reading_text(doc))
    ]


def _reading_text(doc: MedicalDocument) -> str:
    """Title, summary, findings and diagnoses of a document's reading."""
    analysis = doc.analysis or {}
    parts = [doc.title, str(analysis.get("summary") or "")]
    parts += [str(x) for x in analysis.get("findings") or []]
    parts += [str(x) for x in analysis.get("conditions") or []]
    return " ".join(parts)


def _document(doc: MedicalDocument) -> dict[str, Any]:
    """A document of the record with the essentials of its reading."""
    analysis = doc.analysis or {}
    return {
        **record_suggest.doc_ref(doc),
        "status": doc.analysis_status,
        "summary": analysis.get("summary"),
        "findings": analysis.get("findings") or [],
        "values": len(analysis.get("values") or []),
    }
