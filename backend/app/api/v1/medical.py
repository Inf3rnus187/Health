"""Medical documents: upload, list, view/download and delete."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, UploadFile, status
from fastapi.responses import Response

from app.core.deps import SessionDep, UserDep
from app.core.errors import InvalidInputError
from app.models.medical import MedicalDocument
from app.schemas.common import Message
from app.schemas.medical import MedicalDocOut, normalize_kind, parse_day
from app.services import audit, document_ai, medical

router = APIRouter(prefix="/medical", tags=["medical"])

_MAX_BYTES = 25 * 1024 * 1024


@router.post(
    "/documents",
    response_model=MedicalDocOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload(
    principal: UserDep,
    session: SessionDep,
    file: UploadFile,
    kind: Annotated[str, Form()] = "autre",
    title: Annotated[str, Form()] = "",
    doc_date: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
) -> MedicalDocument:
    """Store an uploaded medical document with its type and date."""
    data = await _read(file)
    meta = {
        "kind": normalize_kind(kind),
        "title": (title.strip() or file.filename or "Document")[:200],
        "doc_date": parse_day(doc_date),
        "notes": notes.strip() or None,
        "media_type": file.content_type or "application/octet-stream",
    }
    doc = await medical.create_document(
        session, principal.user.id, meta=meta, data=data
    )
    await audit.record(
        session,
        action="create",
        entity="medical_document",
        user_id=principal.user.id,
        entity_id=doc.id,
    )
    await session.commit()
    await document_ai.queue(session, doc)
    return doc


@router.get("/documents", response_model=list[MedicalDocOut])
async def index(
    principal: UserDep, session: SessionDep
) -> list[MedicalDocument]:
    """List the caller's medical documents, newest first."""
    return await medical.list_documents(session, principal.user.id)


@router.get("/documents/{doc_id}/file")
async def download(
    doc_id: str, principal: UserDep, session: SessionDep
) -> Response:
    """Return one document's decrypted bytes for viewing/download."""
    doc = await medical.get_document(session, principal.user.id, doc_id)
    disposition = f'inline; filename="{doc.id}"'
    return Response(
        content=medical.read_file(doc),
        media_type=doc.media_type,
        headers={"Content-Disposition": disposition},
    )


@router.delete("/documents/{doc_id}", response_model=Message)
async def delete(
    doc_id: str, principal: UserDep, session: SessionDep
) -> Message:
    """Delete one of the caller's medical documents."""
    await medical.delete_document(session, principal.user.id, doc_id)
    await audit.record(
        session,
        action="delete",
        entity="medical_document",
        user_id=principal.user.id,
        entity_id=doc_id,
    )
    await session.commit()
    return Message(detail="deleted")


async def _read(file: UploadFile) -> bytes:
    """Read an upload, enforcing the size cap."""
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise InvalidInputError("Fichier trop volumineux (max 25 Mo)")
    return data
