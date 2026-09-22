"""Account endpoints: RGPD erasure (§12)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import InteractiveDep, SessionDep
from app.schemas.common import Message
from app.services import account, audit

router = APIRouter(tags=["account"])


@router.delete("/me", response_model=Message)
async def erase_account(
    principal: InteractiveDep, session: SessionDep
) -> Message:
    """Permanently erase the caller's account and all their data."""
    await audit.record(session, action="erase", entity="user", actor="user")
    await account.erase(session, principal.user)
    await session.commit()
    return Message(detail="account erased")
