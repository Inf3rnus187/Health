"""Evidence: calls, messages, mails, screenshots, notes, documents."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import ReaderDep, SessionDep, UserDep
from app.core.errors import InvalidInputError, NotFoundError
from app.models.work import Evidence
from app.schemas.workfile import EvidenceOut, EvidenceUpdate
from app.services import evidence
from app.services.daily_rollup import user_zone

router = APIRouter(prefix="/evidence", tags=["evidence"])

_MAX_BYTES = 30 * 1024 * 1024


@router.get("", response_model=list[EvidenceOut])
async def index(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[Evidence]:
    """Evidence between two days (all by default), oldest first."""
    return await evidence.list_items(session, principal.user.id, start, end)


def _form(
    occurred_at: Annotated[datetime, Form()],
    kind: Annotated[str, Form()] = "capture",
    title: Annotated[str, Form(max_length=200)] = "",
    description: Annotated[str, Form(max_length=8000)] = "",
    count: Annotated[int, Form(ge=1, le=10000)] = 1,
    absence_id: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """The item's details from the form."""
    if kind not in evidence.KINDS:
        raise InvalidInputError(f"kind must be one of {sorted(evidence.KINDS)}")
    return {
        "occurred_at": occurred_at,
        "kind": kind,
        "title": title,
        "description": description,
        "count": count,
        "absence_id": absence_id or None,
    }


@router.post(
    "", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED
)
async def create(
    principal: UserDep,
    session: SessionDep,
    fields: Annotated[dict[str, Any], Depends(_form)],
    file: UploadFile | None = None,
) -> Evidence:
    """Add a proof (file optional): when, what, how many (12 calls…)."""
    tz = await user_zone(session, principal.user.id)
    when = fields["occurred_at"]
    if when.tzinfo is None:  # a local time typed in a form
        when = when.replace(tzinfo=tz)
    fields["occurred_at"] = when.astimezone(UTC)
    upload = None
    if file is not None and file.filename:
        data = await file.read()
        if len(data) > _MAX_BYTES:
            raise InvalidInputError("File over 30 MB")
        upload = (file.filename, file.content_type or "", data)
    row = await evidence.create(session, principal.user.id, fields, upload)
    await session.commit()
    return row


@router.get("/{item_id}/file")
async def download(
    item_id: str, principal: ReaderDep, session: SessionDep
) -> Response:
    """The item's file, as received."""
    row = await evidence.get(session, principal.user.id, item_id)
    data = evidence.read_file(row)
    if data is None:
        raise NotFoundError("No file for this evidence")
    name = (row.file_name or "preuve").replace('"', "")
    return Response(
        content=data,
        media_type=row.media_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


@router.put("/{item_id}", response_model=EvidenceOut)
async def edit(
    item_id: str,
    body: EvidenceUpdate,
    principal: UserDep,
    session: SessionDep,
) -> Evidence:
    """Fix an item's details (its file and fingerprint do not change)."""
    row = await evidence.get(session, principal.user.id, item_id)
    changes = body.model_dump(exclude_unset=True)
    when = changes.get("occurred_at")
    if when is not None:
        tz = await user_zone(session, principal.user.id)
        aware = when if when.tzinfo else when.replace(tzinfo=tz)
        changes["occurred_at"] = aware.astimezone(UTC)
    for key, value in changes.items():
        setattr(row, key, value)
    await session.commit()
    return row


@router.delete("/{item_id}")
async def remove(
    item_id: str, principal: UserDep, session: SessionDep
) -> dict[str, str]:
    """Delete an item and its file."""
    await evidence.delete(session, principal.user.id, item_id)
    await session.commit()
    return {"detail": "deleted"}
