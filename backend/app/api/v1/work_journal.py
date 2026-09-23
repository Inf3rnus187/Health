"""Work: the day-by-day journal; two sessions of the same work made one."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.schemas.work import MergeIn, WorkSessionOut
from app.services import work_journal, work_merge
from app.services.timed_entries import local_day

router = APIRouter(prefix="/work", tags=["work"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]

#: Longest journal asked at once.
_MAX_DAYS = 800


@router.get("/days")
async def days(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[dict[str, Any]]:
    """One line per day (default: the last 30), oldest first.

    The night before (asleep, awakenings, wake-up), first clock-in, last
    clock-out, hours worked and the remote part, bedtime that evening,
    absence or public holiday, the day's proofs and traces, and the
    state (complete, to complete, at work now).
    """
    user_id = principal.user.id
    last = end or await local_day(session, user_id, utcnow())
    first = start or last - timedelta(days=29)
    first = max(first, last - timedelta(days=_MAX_DAYS))
    return await work_journal.journal(session, user_id, first, last)


@router.post("/sessions/{session_id}/merge", response_model=WorkSessionOut)
async def merge(
    session_id: str, body: MergeIn, principal: WriteDep, session: SessionDep
) -> dict[str, Any]:
    """Make another session of the same place part of this one.

    The first clock-in and the last clock-out of the two are kept (a lone
    embauche of 09:02 and a lone débauche of 19:12 become 09:02 → 19:12);
    the other session is deleted and the note says what it held.
    """
    row = await work_merge.merge(
        session, principal.user.id, session_id, body.other_id
    )
    await session.commit()
    return row
