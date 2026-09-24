"""The facts of a period, as a report proves them (JSON)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.services import report_facts
from app.services.timed_entries import local_day

router = APIRouter(tags=["reports"])
_DAYS = 90


@router.get("/facts")
async def facts(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    compare_from: Annotated[date | None, Query()] = None,
) -> dict[str, Any]:
    """What was recorded over a period (default: the last 90 days).

    ``habits``: per counter (cigarettes, urges broken, coffee, water,
    pees) days with and **without** an entry, total, mean per recorded
    day, median, lowest / highest day, per week or month, and with
    ``compare_from`` before / after that day (means, change %).
    ``medications``: adherence per treatment. ``meals``: counts, share
    read by the AI, daily means, scores, value sources, foods eaten
    most, meals entered late. ``trace``: when and how the entries were
    made (at the time, the same day, later; site, Shortcut, MCP).
    """
    user_id = principal.user.id
    last = end or await local_day(session, user_id, utcnow())
    first = start or last - timedelta(days=_DAYS - 1)
    if first > last:
        raise InvalidInputError("start is after end")
    return await report_facts.gather(
        session, user_id, (first, last), compare_from
    )
