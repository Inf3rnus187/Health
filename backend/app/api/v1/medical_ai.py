"""AI reading of medical documents: (re-)analyse, read the text."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.services import document_ai, document_text, medical

router = APIRouter(prefix="/medical", tags=["medical"])
_TEXT_MAX = 200_000  # characters returned (a long report fits)


@router.post("/documents/analyze-all", status_code=status.HTTP_202_ACCEPTED)
async def analyze_all(
    principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Queue every document of the caller for AI reading."""
    docs = await medical.list_documents(session, principal.user.id)
    queued = 0
    for doc in docs:
        queued += int(await document_ai.queue(session, doc))
    return {"queued": queued}


@router.post(
    "/documents/{doc_id}/analyze", status_code=status.HTTP_202_ACCEPTED
)
async def analyze(
    doc_id: str, principal: UserDep, session: SessionDep
) -> dict[str, str]:
    """Queue one document for (re-)analysis by the document model."""
    doc = await medical.get_document(session, principal.user.id, doc_id)
    queued = await document_ai.queue(session, doc)
    return {"status": "queued" if queued else "unavailable"}


@router.get("/documents/{doc_id}/text")
async def text(
    doc_id: str, principal: UserDep, session: SessionDep
) -> dict[str, Any]:
    """The text the AI reads from a document (OCR for a scan)."""
    doc = await medical.get_document(session, principal.user.id, doc_id)
    content = document_text.extract(medical.read_file(doc), doc.media_type)
    return {
        "id": doc.id,
        "title": doc.title,
        "scanned": content.scanned,
        "images": len(content.images),
        "text": content.text[:_TEXT_MAX],
    }
