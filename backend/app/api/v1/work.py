"""Work hours: clock in / out and the sessions (occupational health)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.schemas.work import (
    ClockIn,
    WorkSessionIn,
    WorkSessionOut,
    WorkSessionUpdate,
)
from app.services import work
from app.services.timed_entries import local_day

router = APIRouter(prefix="/work", tags=["work"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]


@router.post("/clock", response_model=WorkSessionOut)
async def clock(
    body: ClockIn, principal: TapDep, session: SessionDep
) -> dict[str, Any]:
    """Clock in or out (now unless ``at`` is given)."""
    row = await work.clock(
        session, principal.user.id, body.kind, body.at, "manual"
    )
    await session.commit()
    return row


@router.get("/sessions", response_model=list[WorkSessionOut])
async def sessions(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[dict[str, Any]]:
    """Sessions between two days (default: the last 30), newest first."""
    last = end or await local_day(session, principal.user.id, utcnow())
    first = start or last - timedelta(days=29)
    return await work.list_sessions(session, principal.user.id, first, last)


@router.post(
    "/sessions",
    response_model=WorkSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add(
    body: WorkSessionIn, principal: WriteDep, session: SessionDep
) -> dict[str, Any]:
    """Add a session typed by hand (same start: that session is updated)."""
    row = await work.add(
        session, principal.user.id, body.model_dump(), "manual"
    )
    await session.commit()
    return row


@router.put("/sessions/{session_id}", response_model=WorkSessionOut)
async def edit(
    session_id: str,
    body: WorkSessionUpdate,
    principal: WriteDep,
    session: SessionDep,
) -> dict[str, Any]:
    """Fix a session's times or note."""
    fields = body.model_dump(exclude_unset=True)
    row = await work.update(session, principal.user.id, session_id, fields)
    await session.commit()
    return row


@router.delete("/sessions/{session_id}")
async def remove(
    session_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete a session."""
    await work.delete(session, principal.user.id, session_id)
    await session.commit()
    return {"detail": "deleted"}
