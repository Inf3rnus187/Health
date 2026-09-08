"""Optional MFA (TOTP) management endpoints (§12.1)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import SessionDep, UserDep
from app.schemas.common import Message
from app.schemas.mfa import MfaSetupOut, MfaVerify
from app.services import mfa

router = APIRouter(prefix="/auth/mfa", tags=["auth"])


@router.post("/setup", response_model=MfaSetupOut)
async def setup(principal: UserDep, session: SessionDep) -> MfaSetupOut:
    """Assign a TOTP secret and return its otpauth URI (not yet enabled)."""
    uri = await mfa.setup(session, principal.user)
    await session.commit()
    return MfaSetupOut(secret=principal.user.mfa_secret or "", otpauth_uri=uri)


@router.post("/enable", response_model=Message)
async def enable(
    body: MfaVerify, principal: UserDep, session: SessionDep
) -> Message:
    """Enable MFA after verifying a code."""
    await mfa.enable(session, principal.user, body.code)
    await session.commit()
    return Message(detail="mfa enabled")


@router.post("/disable", response_model=Message)
async def disable(
    body: MfaVerify, principal: UserDep, session: SessionDep
) -> Message:
    """Disable MFA after verifying a code."""
    await mfa.disable(session, principal.user, body.code)
    await session.commit()
    return Message(detail="mfa disabled")
