"""Nights of sleep: awakenings, blocks, and nights typed by hand."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.core.deps import ReaderDep, SessionDep, UserDep
from app.models.base import utcnow
from app.services import sleep_manual, sleep_nights
from app.services.daily_rollup import user_zone
from app.services.timed_entries import local_day

router = APIRouter(prefix="/sleep", tags=["sleep"])


class TypedNight(BaseModel):
    """A night typed by hand (times without offset: local)."""

    bedtime: datetime
    wake_time: datetime
    awakenings: int | None = Field(default=None, ge=0, le=100)


@router.get("/nights")
async def nights(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    missing: Annotated[bool, Query()] = True,
) -> list[dict[str, Any]]:
    """Nights by wake-up day, newest first (default: since the first one).

    Days of the period without any sleep data are listed as missing
    (``missing=false`` leaves them out).
    """
    user_id = principal.user.id
    tz = await user_zone(session, user_id)
    last = end or await local_day(session, user_id, utcnow())
    known = await sleep_nights.first_day(session, user_id, tz)
    first = start or known or last - timedelta(days=29)
    found = await sleep_nights.nights(session, user_id, first, last, tz)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return [
        sleep_nights.as_dict(found[d]) if d in found
        else {"wake_day": d, "missing": True}
        for d in reversed(days)
        if d in found or missing
    ]  # fmt: skip


@router.get("/typed")
async def typed(
    principal: ReaderDep, session: SessionDep
) -> list[dict[str, Any]]:
    """The nights typed by hand, newest first."""
    return await sleep_manual.typed(session, principal.user.id)


@router.post("/nights", status_code=status.HTTP_201_CREATED)
async def add_night(
    body: TypedNight, principal: UserDep, session: SessionDep
) -> dict[str, Any]:
    """Type a night the watch missed (bedtime, wake-up, awakenings)."""
    row = await sleep_manual.add(
        session, principal.user.id, body.bedtime, body.wake_time,
        body.awakenings,
    )  # fmt: skip
    await session.commit()
    return row


@router.delete("/nights/{night_id}")
async def remove_night(
    night_id: str, principal: UserDep, session: SessionDep
) -> dict[str, str]:
    """Delete a night typed by hand."""
    await sleep_manual.remove(session, principal.user.id, night_id)
    await session.commit()
    return {"detail": "deleted"}
