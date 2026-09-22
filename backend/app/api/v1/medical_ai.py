"""AI reading of medical documents: (re-)analyse one or all documents."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.services import document_ai, medical

router = APIRouter(prefix="/medical", tags=["medical"])


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
