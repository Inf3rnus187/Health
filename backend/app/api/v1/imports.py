"""Apple Health import: upload (async job), status polling and reset."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status

from app.core.config import get_settings
from app.core.deps import (
    Principal,
    SessionDep,
    require_scope,
    require_scope_flex,
)
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import new_uuid
from app.models.health_raw import ImportJob
from app.schemas.common import Message
from app.schemas.imports import ImportJobOut
from app.services import audit, imports, samples
from app.workers.queue import enqueue

router = APIRouter(prefix="/imports", tags=["imports"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
UploadDep = Annotated[
    Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))
]
_CHUNK = 1 << 20


@router.post(
    "/apple-health",
    response_model=ImportJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload(
    principal: UploadDep, session: SessionDep, file: UploadFile
) -> ImportJob:
    """Store the uploaded export and queue a background import.

    Accepts the token in the ``Authorization`` header or a ``?token=``
    query param, so an iPhone Shortcut can upload with just a URL.
    """
    safe = _safe_name(file.filename or "export")
    path = await _stream_to_disk(file, safe)
    job = await imports.create_job(session, principal.user.id, safe, path)
    await audit.record(
        session,
        action="import",
        entity="apple_health",
        user_id=principal.user.id,
        entity_id=job.id,
    )
    await enqueue("import_apple_health_job", job.id)
    return job


@router.get("", response_model=list[ImportJobOut])
async def index(principal: WriteDep, session: SessionDep) -> list[ImportJob]:
    """List the caller's recent import jobs."""
    return await imports.list_jobs(session, principal.user.id)


@router.get("/{job_id}", response_model=ImportJobOut)
async def get(
    job_id: str, principal: WriteDep, session: SessionDep
) -> ImportJob:
    """Return the status of one import job."""
    return await imports.get_job(session, principal.user.id, job_id)


@router.post("/reset", response_model=Message)
async def reset(principal: WriteDep, session: SessionDep) -> Message:
    """Delete every Apple-imported sample, workout, ECG and route."""
    await samples.wipe_imported(session, principal.user.id)
    await audit.record(
        session,
        action="reset",
        entity="apple_health",
        user_id=principal.user.id,
    )
    await session.commit()
    return Message(detail="cleared")


def _safe_name(name: str) -> str:
    """Return a filesystem-safe basename for an upload."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)
    return cleaned[:120] or "export"


async def _stream_to_disk(file: UploadFile, safe: str) -> str:
    """Stream the upload to the exports volume in fixed-size chunks."""
    base = Path(get_settings().exports_dir) / "imports"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{new_uuid()}_{safe}"
    with path.open("wb") as out:
        while chunk := await file.read(_CHUNK):
            out.write(chunk)
    return str(path)
