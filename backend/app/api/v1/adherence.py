"""Medication adherence: today's doses, and a period's per treatment."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.services import medication_stats

router = APIRouter(prefix="/medications", tags=["care"])


@router.get("/today")
async def today(principal: ReaderDep, session: SessionDep) -> list[Any]:
    """The active treatments with today's doses (taken, not taken, last)."""
    return await medication_stats.today(session, principal.user.id)


@router.get("/adherence")
async def adherence(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> dict[str, Any]:
    """Adherence per treatment over a period (default: the last 30 days).

    Planned doses (days × ``doses_per_day``), taken, not taken, rate,
    days complete, days without any record, longest gap, usual time,
    doses entered more than an hour late, per week.
    """
    user_id = principal.user.id
    span = await medication_stats.span(session, user_id, start, end)
    return await medication_stats.adherence(session, user_id, span)
