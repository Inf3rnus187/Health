"""Conditions (maladies) CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.models.medical import Condition
from app.schemas.care import ConditionIn, ConditionOut
from app.schemas.common import Message
from app.services import conditions as svc

router = APIRouter(prefix="/conditions", tags=["care"])


@router.post(
    "", response_model=ConditionOut, status_code=status.HTTP_201_CREATED
)
async def create(
    body: ConditionIn, principal: UserDep, session: SessionDep
) -> Condition:
    """Declare a condition."""
    row = await svc.create(session, principal.user.id, body)
    await session.commit()
    return row


@router.get("", response_model=list[ConditionOut])
async def index(principal: UserDep, session: SessionDep) -> list[Condition]:
    """List the caller's conditions."""
    return await svc.list_all(session, principal.user.id)


@router.put("/{cid}", response_model=ConditionOut)
async def update(
    cid: str, body: ConditionIn, principal: UserDep, session: SessionDep
) -> Condition:
    """Replace a condition."""
    row = await svc.update(session, principal.user.id, cid, body)
    await session.commit()
    return row


@router.delete("/{cid}", response_model=Message)
async def delete(cid: str, principal: UserDep, session: SessionDep) -> Message:
    """Delete a condition."""
    await svc.delete(session, principal.user.id, cid)
    await session.commit()
    return Message(detail="deleted")
