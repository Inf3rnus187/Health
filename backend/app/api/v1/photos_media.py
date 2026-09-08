"""Photo upload and authenticated file serving (§8, §12)."""

from __future__ import annotations

import mimetypes
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, status
from fastapi.responses import Response

from app.core.deps import (
    Principal,
    PrincipalDep,
    SessionDep,
    require_scope,
)
from app.core.scopes import INGEST_PHOTO
from app.models.photo import Photo
from app.schemas.photo import PhotoOut
from app.services import audit, photo_intake, photo_storage
from app.services import photos as svc
from app.workers.queue import enqueue

router = APIRouter(tags=["photos"])

UploadDep = Annotated[Principal, Depends(require_scope(INGEST_PHOTO))]


@router.post(
    "/ingest/photo",
    response_model=PhotoOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload(
    principal: UploadDep,
    session: SessionDep,
    file: UploadFile,
    angle: Annotated[str, Form()] = "face",
    date_key: Annotated[date | None, Form()] = None,
    weight: Annotated[float | None, Form()] = None,
) -> Photo:
    """Receive a photo, store it, and queue the analysis pipeline."""
    photo = await photo_intake.intake(
        session,
        principal.user.id,
        content_type=file.content_type or "",
        data=await file.read(),
        angle=angle,
        date_key=date_key,
        weight=weight,
    )
    await audit.record(
        session,
        action="upload",
        entity="photo",
        user_id=principal.user.id,
        entity_id=photo.id,
    )
    await session.commit()
    await enqueue("analyze_photo", photo.id)
    return photo


@router.get("/photos/{photo_id}/file")
async def download(
    photo_id: str, principal: PrincipalDep, session: SessionDep
) -> Response:
    """Return a photo's file (decrypted, normalized if ready) to its owner."""
    photo = await svc.get_photo(session, principal.user.id, photo_id)
    path = photo.normalized_path or photo.original_path
    data = photo_storage.read_bytes(Path(path))
    media = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return Response(content=data, media_type=media)
