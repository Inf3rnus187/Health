"""Biology import: parse a lab PDF into tracked series, keep the file."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, UploadFile

from app.core.deps import SessionDep, UserDep
from app.services import audit, biology, medical

router = APIRouter(prefix="/biology", tags=["biology"])


@router.post("/import")
async def import_biology(
    principal: UserDep, session: SessionDep, file: UploadFile
) -> dict[str, Any]:
    """Parse a lab PDF into measurements and keep the source document."""
    data = await file.read()
    summary = await biology.import_pdf(session, principal.user.id, data)
    await _keep(session, principal.user.id, file, data)
    await audit.record(
        session,
        action="import",
        entity="biology",
        user_id=principal.user.id,
        payload={"added": summary["added"]},
    )
    await session.commit()
    return summary


@router.delete("/values")
async def purge_biology(
    principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Delete all imported biology values and their bio.* metrics."""
    result = await biology.purge(session, principal.user.id)
    await audit.record(
        session,
        action="delete",
        entity="biology",
        user_id=principal.user.id,
        payload=result,
    )
    await session.commit()
    return result


async def _keep(
    session: SessionDep, user_id: str, file: UploadFile, data: bytes
) -> None:
    """Store the uploaded lab PDF as a biologie medical document."""
    meta = {
        "kind": "biologie",
        "title": (file.filename or "Analyse biologique")[:200],
        "doc_date": None,
        "notes": None,
        "media_type": file.content_type or "application/pdf",
    }
    await medical.create_document(session, user_id, meta=meta, data=data)
