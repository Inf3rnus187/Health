"""Automation execution endpoint (NFC/Shortcut trigger, §7.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import (
    Principal,
    SessionDep,
    require_scope,
)
from app.core.scopes import WRITE_MEASUREMENTS
from app.services import automation_runner
from app.services import automations as svc

router = APIRouter(prefix="/automations", tags=["automations"])

RunDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("/{automation_id}/run")
async def run(
    automation_id: str, principal: RunDep, session: SessionDep
) -> dict[str, object]:
    """Execute an automation's action and return a result summary."""
    automation = await svc.get_automation(
        session, principal.user.id, automation_id
    )
    is_user = principal.source == "jwt"
    result = await automation_runner.run(
        session,
        principal.user.id,
        automation,
        source="manual" if is_user else "script",
        token_id=principal.token_id,
    )
    await session.commit()
    return result
