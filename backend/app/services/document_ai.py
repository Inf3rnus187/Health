"""Read an uploaded medical document into tracked values (§8, §11).

1. Exact readers first: the lab parser (current + previous results) and
   the FibroScan reader. Their values are exact.
2. The document model (e.g. MedGemma 1.5) proposes the values the
   parsers missed; each must be proven by the text (metric, unit, number
   AND date printed) or it is rejected — with the reason, never stored.
3. The text model (e.g. MedGemma 27B) writes the French summary and
   lists medications / diagnoses, given only the verified values.

States: queued → running → done | failed (with the error). A reading has
a time limit and the worker re-queues readings a restart interrupted.
Values land in the same ``bio.*`` / ``liver.*`` / ``body.*`` metrics as
any other source, so markers, charts and exports see them.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.medical import MedicalDocument
from app.schemas.medical import KINDS
from app.services import (
    biology,
    document_facts,
    document_prompt,
    document_reading,
    document_text,
    medical,
)
from app.services import document_grounding as grounding
from app.workers.queue import enqueue, enqueue_many

_log = get_logger("document_ai")
_KIND_OF = {"fibroscan": "imagerie"}
_TIME_LIMIT = 1800.0  # seconds for one document, all model calls included
PENDING = ("queued", "running")


async def queue(session: AsyncSession, doc: MedicalDocument) -> bool:
    """Mark a document for (re-)analysis and hand it to the worker."""
    doc.analysis_status = "queued"
    await session.commit()
    if await enqueue("analyze_document", doc.id):
        return True
    doc.analysis_status = None
    await session.commit()
    return False


async def run(session: AsyncSession, doc_id: str) -> None:
    """Worker entry point: analyse one document, record the outcome."""
    doc = await session.get(MedicalDocument, doc_id)
    if doc is None:
        return
    started = utcnow()
    doc.analysis_status, doc.analysis = "running", {"started_at": _iso()}
    await session.commit()
    try:
        result = await asyncio.wait_for(analyze(session, doc), _TIME_LIMIT)
    except Exception as exc:  # noqa: BLE001 - reported on the document
        await _fail(session, doc_id, exc)
        return
    result["duration_s"] = round((utcnow() - started).total_seconds())
    doc.analysis, doc.analysis_status = result, "done"
    await session.commit()


async def analyze(
    session: AsyncSession, doc: MedicalDocument
) -> dict[str, Any]:
    """Read, extract, ground, store and summarise one document."""
    content = document_text.extract(medical.read_file(doc), doc.media_type)
    day = document_facts.document_day(doc, content.text)
    exact = document_facts.exact(content.text, doc.kind, day)
    proposed, values_error = await document_reading.extract_values(content)
    proven, rejected = grounding.ground(proposed, content.text, _units())
    extra = document_facts.new_readings(proven, exact)
    await biology.store(session, doc.user_id, exact, source="document")
    await biology.store(session, doc.user_id, extra, source="document-ai")
    facts = [document_facts.fact(r) for r in exact + extra]
    summary, summary_error = await document_reading.summarize(
        content.text, facts
    )
    _classify(doc, summary, day, content.text)
    return {
        **summary,
        "model": ollama.document_model(),
        "summary_model": ollama.text_model(),
        "scanned": content.scanned,
        "values": [document_facts.row(r, "lecture") for r in exact]
        + [document_facts.row(r, "ia") for r in extra],
        "rejected": len(rejected),
        "rejected_items": rejected,
        "ai_error": values_error or summary_error,
        "finished_at": _iso(),
    }


async def requeue_stale(session: AsyncSession) -> int:
    """Re-queue readings a worker restart left queued / running."""
    result = await session.execute(
        select(MedicalDocument.id).where(
            MedicalDocument.analysis_status.in_(PENDING)
        )
    )
    ids = [(doc_id,) for doc_id in result.scalars().all()]
    return await enqueue_many("analyze_document", ids) if ids else 0


async def _fail(session: AsyncSession, doc_id: str, exc: Exception) -> None:
    """Record a failed reading (the error is shown on the document)."""
    reason = "délai dépassé" if isinstance(exc, TimeoutError) else str(exc)
    _log.warning("document_analysis_failed", doc=doc_id, error=reason)
    await session.rollback()
    doc = await session.get(MedicalDocument, doc_id)
    if doc is not None:
        doc.analysis_status = "failed"
        doc.analysis = {"error": reason[:300], "finished_at": _iso()}
        await session.commit()


def _units() -> dict[str, str]:
    """Allowed metric keys and their units."""
    return {key: unit for key, (_, unit) in document_prompt.allowed().items()}


def _classify(
    doc: MedicalDocument, answer: dict[str, Any], day: date, text: str
) -> None:
    """Fill a missing date / generic kind from what the document proves."""
    if doc.doc_date is None and grounding.date_in(day, text):
        doc.doc_date = day
    kind = str(answer.get("document_type") or "")
    kind = _KIND_OF.get(kind, kind)
    if doc.kind == "autre" and kind in KINDS:
        doc.kind = kind


def _iso() -> str:
    """Now, ISO-formatted (UTC)."""
    return utcnow().isoformat()
