"""Mode B capture endpoint (NFC / Shortcut / button → §7.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import Principal, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.capture import CaptureRequest, CaptureResponse
from app.services import audit
from app.services import capture as svc

router = APIRouter(tags=["capture"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post(
    "/capture",
    response_model=CaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def capture(
    body: CaptureRequest, principal: WriteDep, session: SessionDep
) -> CaptureResponse:
    """Start a capture session and return the day's complement form."""
    is_user = principal.source == "jwt"
    result = await svc.capture(
        session,
        principal.user.id,
        body,
        source="manual" if is_user else "script",
        token_id=principal.token_id,
    )
    await audit.record(
        session,
        action="capture",
        entity="event",
        user_id=principal.user.id,
        entity_id=result.event_id,
    )
    await session.commit()
    return result
