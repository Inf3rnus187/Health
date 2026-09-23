"""Pee log: one tap (web or iPhone Shortcut) = one timed entry."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.schemas.journal import UrinationIn
from app.services import urination
from app.services.timed_entries import local_day

router = APIRouter(prefix="/journal", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]


@router.post("/urination", status_code=status.HTTP_201_CREATED)
async def log_urination(
    principal: TapDep, session: SessionDep, body: UrinationIn | None = None
) -> dict[str, Any]:
    """Record one urination (now unless ``at`` is given)."""
    at = body.at if body else None
    entry = await urination.log(session, principal.user.id, at)
    await session.commit()
    items = await urination.day_list(session, principal.user.id, entry["day"])
    return {**entry, "count": len(items)}


@router.get("/urination")
async def urinations(
    principal: ReaderDep,
    session: SessionDep,
    day: Annotated[date | None, Query()] = None,
) -> dict[str, Any]:
    """A day's urinations (default today) with their times."""
    when = day or await local_day(session, principal.user.id, utcnow())
    items = await urination.day_list(session, principal.user.id, when)
    return {"day": when, "count": len(items), "items": items}


@router.delete("/urination/{sample_id}")
async def delete_urination(
    sample_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete one urination entry."""
    await urination.remove(session, principal.user.id, sample_id)
    await session.commit()
    return {"detail": "deleted"}
