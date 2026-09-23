"""The daily journal, one line per day (sleep, water, coffee, meals…)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.services import journal_days
from app.services.timed_entries import local_day

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/days")
async def days(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=400)] = 31,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Journal lines of ``start``..``end`` (newest first), a page at a time.

    Each line: the night ended that morning (asleep, in how many goes,
    awakenings, bedtime → wake-up), water (bottles and litres), coffees,
    cigarettes, pees, meals (count, energy). ``total`` is the number of
    days of the period. Without ``start``: from the first day recorded;
    without ``end``: up to today.
    """
    user_id = principal.user.id
    last = end or await local_day(session, user_id, utcnow())
    first = start or await journal_days.first_day(session, user_id) or last
    if first > last:
        raise InvalidInputError("start is after end")
    return await journal_days.page(
        session, user_id, (first, last), (limit, offset)
    )
