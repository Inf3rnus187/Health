"""The medical record (Dossier) and the condition follow-up (Suivi)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.deps import SessionDep, UserDep
from app.services import medical_record

router = APIRouter(tags=["medical"])


@router.get("/medical/record")
async def record(principal: UserDep, session: SessionDep) -> dict[str, Any]:
    """Documents, suggestions, results and chronology of the caller."""
    return await medical_record.record(session, principal.user.id)


@router.get("/care/overview")
async def care(principal: UserDep, session: SessionDep) -> list[dict[str, Any]]:
    """Each declared condition with its indicators and documents."""
    return await medical_record.care(session, principal.user.id)
