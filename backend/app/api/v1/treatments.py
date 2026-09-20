"""Treatments (traitements) CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.models.medical import Treatment
from app.schemas.care import TreatmentIn, TreatmentOut
from app.schemas.common import Message
from app.services import treatments as svc

router = APIRouter(prefix="/treatments", tags=["care"])


@router.post(
    "", response_model=TreatmentOut, status_code=status.HTTP_201_CREATED
)
async def create(
    body: TreatmentIn, principal: UserDep, session: SessionDep
) -> Treatment:
    """Add a treatment."""
    row = await svc.create(session, principal.user.id, body)
    await session.commit()
    return row


@router.get("", response_model=list[TreatmentOut])
async def index(principal: UserDep, session: SessionDep) -> list[Treatment]:
    """List the caller's treatments."""
    return await svc.list_all(session, principal.user.id)


@router.put("/{tid}", response_model=TreatmentOut)
async def update(
    tid: str, body: TreatmentIn, principal: UserDep, session: SessionDep
) -> Treatment:
    """Replace a treatment (e.g. toggle active, change dose)."""
    row = await svc.update(session, principal.user.id, tid, body)
    await session.commit()
    return row


@router.delete("/{tid}", response_model=Message)
async def delete(tid: str, principal: UserDep, session: SessionDep) -> Message:
    """Delete a treatment."""
    await svc.delete(session, principal.user.id, tid)
    await session.commit()
    return Message(detail="deleted")
