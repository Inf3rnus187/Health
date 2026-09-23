"""Work: the day-by-day journal (night, work, absence, proofs)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.models.base import utcnow
from app.services import work_journal
from app.services.timed_entries import local_day

router = APIRouter(prefix="/work", tags=["work"])

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
