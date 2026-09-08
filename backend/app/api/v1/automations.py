"""Automation CRUD endpoints (§7.2)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.models.automation import Automation
from app.schemas.automation import (
    AutomationCreate,
    AutomationOut,
    AutomationUpdate,
)
from app.schemas.common import Message
from app.services import audit
from app.services import automations as svc

router = APIRouter(prefix="/automations", tags=["automations"])


@router.post(
    "", response_model=AutomationOut, status_code=status.HTTP_201_CREATED
)
async def create(
    body: AutomationCreate, principal: UserDep, session: SessionDep
) -> Automation:
    """Create a new automation."""
    automation = await svc.create_automation(session, principal.user.id, body)
    await audit.record(
        session,
        action="create",
        entity="automation",
        user_id=principal.user.id,
        entity_id=automation.id,
    )
    await session.commit()
    return automation


@router.get("", response_model=list[AutomationOut])
async def index(principal: UserDep, session: SessionDep) -> list[Automation]:
    """List the caller's automations."""
    return await svc.list_automations(session, principal.user.id)


@router.get("/{automation_id}", response_model=AutomationOut)
async def detail(
    automation_id: str, principal: UserDep, session: SessionDep
) -> Automation:
    """Return one automation."""
    return await svc.get_automation(session, principal.user.id, automation_id)


@router.patch("/{automation_id}", response_model=AutomationOut)
async def update(
    automation_id: str,
    body: AutomationUpdate,
    principal: UserDep,
    session: SessionDep,
) -> Automation:
    """Update an automation's name, action or active flag."""
    automation = await svc.update_automation(
        session, principal.user.id, automation_id, body
    )
    await session.commit()
    return automation


@router.delete("/{automation_id}", response_model=Message)
async def delete(
    automation_id: str, principal: UserDep, session: SessionDep
) -> Message:
    """Delete an automation."""
    await svc.delete_automation(session, principal.user.id, automation_id)
    await session.commit()
    return Message(detail="deleted")
