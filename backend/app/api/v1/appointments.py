"""Appointments (rendez-vous) endpoints, incl. Apple Calendar .ics import."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, status

from app.core.deps import SessionDep, UserDep
from app.models.medical import Appointment
from app.schemas.care import AppointmentIn, AppointmentOut
from app.schemas.common import Message
from app.services import appointments as svc

router = APIRouter(prefix="/appointments", tags=["care"])


@router.post(
    "", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED
)
async def create(
    body: AppointmentIn, principal: UserDep, session: SessionDep
) -> Appointment:
    """Add a manual appointment."""
    row = await svc.create(session, principal.user.id, body)
    await session.commit()
    return row


@router.get("", response_model=list[AppointmentOut])
async def index(principal: UserDep, session: SessionDep) -> list[Appointment]:
    """List the caller's appointments."""
    return await svc.list_all(session, principal.user.id)


@router.post("/import", response_model=dict[str, int])
async def import_ics(
    principal: UserDep, session: SessionDep, file: UploadFile
) -> dict[str, int]:
    """Import appointments from an Apple Calendar (.ics) export."""
    text = (await file.read()).decode("utf-8", "replace")
    added = await svc.import_ics(session, principal.user.id, text)
    await session.commit()
    return {"added": added}


@router.delete("/{aid}", response_model=Message)
async def delete(aid: str, principal: UserDep, session: SessionDep) -> Message:
    """Delete an appointment."""
    await svc.delete(session, principal.user.id, aid)
    await session.commit()
    return Message(detail="deleted")
