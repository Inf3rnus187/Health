"""Read an uploaded medical document into tracked values (§8, §11).

1. Deterministic readers first: the lab parser (current + previous
   results) and the FibroScan reader. Their values are exact.
2. Then the document model (e.g. MedGemma 1.5, which was trained on lab
   report extraction) proposes the values the parsers missed, plus the
   document type and a short summary.
3. Every AI-proposed value must be proven by the document text (metric,
   unit, number AND date printed) or it is rejected — never stored.

Values land in the same ``bio.*`` / ``liver.*`` metrics as a lab import,
so the markers, charts and exports see them like any other value.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.core.logging import get_logger
from app.models.medical import MedicalDocument
from app.schemas.medical import KINDS
from app.services import (
    biology,
    document_prompt,
    document_text,
    fibroscan,
    medical,
)
from app.services import document_grounding as grounding
from app.services.biology import Reading
from app.services.document_text import DocContent
from app.workers.queue import enqueue

_log = get_logger("document_ai")
_KIND_OF = {"fibroscan": "imagerie"}
_SUMMARY_MAX = 600


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
    try:
        doc.analysis = await analyze(session, doc)
        doc.analysis_status = "done"
    except Exception as exc:  # noqa: BLE001 - reported on the document
        _log.warning("document_analysis_failed", doc=doc_id, error=str(exc))
        await session.rollback()
        doc = await session.get(MedicalDocument, doc_id)
        if doc is None:
            return
        doc.analysis_status = "failed"
        doc.analysis = {"error": str(exc)[:300]}
    await session.commit()


async def analyze(
    session: AsyncSession, doc: MedicalDocument
) -> dict[str, Any]:
    """Read, extract, ground and store one document's values."""
    content = document_text.extract(medical.read_file(doc), doc.media_type)
    day = _document_day(doc, content.text)
    exact = _deterministic(content.text, doc.kind, day)
    answer, error = await _ask(content)
    proven, rejected = grounding.ground(
        answer.get("values"), content.text, _units()
    )
    extra = _new_readings(proven, exact)
    await biology.store(session, doc.user_id, exact, source="document")
    await biology.store(session, doc.user_id, extra, source="document-ai")
    _classify(doc, answer, day, content.text)
    return {
        "model": ollama.document_model() if error is None else None,
        "document_type": str(answer.get("document_type") or "") or None,
        "summary": str(answer.get("summary") or "")[:_SUMMARY_MAX] or None,
        "scanned": content.scanned,
        "values": [_row(r, "lecture") for r in exact]
        + [_row(r, "ia") for r in extra],
        "rejected": rejected,
        "ai_error": error,
    }


def _document_day(doc: MedicalDocument, text: str) -> date:
    """The document's date: given, printed, else its upload day."""
    return (
        doc.doc_date
        or biology.sample_date(text)
        or fibroscan.exam_date(text)
        or doc.created_at.date()
    )


def _deterministic(text: str, kind: str, day: date) -> list[Reading]:
    """Values read by the exact parsers (lab report, FibroScan)."""
    lab_day = biology.sample_date(text)
    out: list[Reading] = []
    if lab_day is not None or kind == "biologie":
        out.extend(biology.parse_text(text, lab_day or day))
    for key, value, when in fibroscan.parse(text, day):
        label, unit = document_prompt.LIVER[key]
        out.append(Reading(key, label, unit, when, value))
    return out


async def _ask(content: DocContent) -> tuple[dict[str, Any], str | None]:
    """The document model's reading, or ``({}, error)`` if unavailable."""
    if not content.text.strip() and not content.images:
        return {}, "document illisible (ni texte ni image)"
    try:
        answer = await ollama.generate_json(
            document_prompt.build(content),
            ollama.document_model(),
            images=content.images,
        )
    except Exception as exc:  # noqa: BLE001 - exact values still count
        return {}, str(exc)[:300]
    return answer, None


def _units() -> dict[str, str]:
    """Allowed metric keys and their units."""
    return {key: unit for key, (_, unit) in document_prompt.allowed().items()}


def _new_readings(
    proven: list[grounding.Grounded], exact: list[Reading]
) -> list[Reading]:
    """Proven AI values the exact parsers did not already find."""
    known = {(r.key, r.day) for r in exact}
    labels = document_prompt.allowed()
    out: list[Reading] = []
    for item in proven:
        if (item.key, item.day) not in known:
            label, unit = labels[item.key]
            out.append(Reading(item.key, label, unit, item.day, item.value))
            known.add((item.key, item.day))
    return out


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


def _row(reading: Reading, origin: str) -> dict[str, Any]:
    """One recorded value, as shown under the document."""
    return {
        "key": reading.key,
        "label": reading.label,
        "value": reading.value,
        "unit": reading.unit,
        "date": reading.day.isoformat(),
        "origin": origin,
    }
