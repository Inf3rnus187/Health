"""Delete many items at once: proofs and traces, sessions, absences, meals.

Only the user's own items go (other ids are ignored); the answer says
how many. A proof's file goes with it, and the meal a delivery was
logged as when asked; the days of deleted sessions are rebuilt.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.work import Absence, Evidence, WorkSession
from app.services import meals as meal_service
from app.services import work_days
from app.services.daily_rollup import user_zone

_CHUNK = 500
Row = TypeVar("Row", Evidence, WorkSession, Absence, Meal)


async def evidence(
    session: AsyncSession, user_id: str, ids: list[str], with_meals: bool
) -> dict[str, int]:
    """Delete proofs and traces, their files, and their meals if asked."""
    rows = await _own(session, Evidence, user_id, ids)
    linked = [row.meal_id for row in rows if row.meal_id]
    for row in rows:
        if row.file_path:
            Path(row.file_path).unlink(missing_ok=True)
        await session.delete(row)
    await session.flush()
    gone = await meals(session, user_id, linked) if with_meals and linked else 0
    return {"deleted": len(rows), "meals": gone}


async def sessions(
    session: AsyncSession, user_id: str, ids: list[str]
) -> dict[str, int]:
    """Delete work sessions and rebuild their days."""
    tz = await user_zone(session, user_id)
    rows = await _own(session, WorkSession, user_id, ids)
    days = {work_days.view(row, tz)["date_key"] for row in rows}
    for row in rows:
        await session.delete(row)
    await session.flush()
    if days:
        await work_days.refresh(session, user_id, days, tz)
    return {"deleted": len(rows)}


async def absences(
    session: AsyncSession, user_id: str, ids: list[str]
) -> dict[str, int]:
    """Delete absences (their evidence stays, unlinked)."""
    rows = await _own(session, Absence, user_id, ids)
    for row in rows:
        await session.delete(row)
    await session.flush()
    return {"deleted": len(rows)}


async def meals(session: AsyncSession, user_id: str, ids: list[str]) -> int:
    """Delete meals, their photos and nutrients; how many went."""
    rows = await _own(session, Meal, user_id, ids)
    for row in rows:
        await meal_service.delete(session, user_id, row.id)
    return len(rows)


async def _own(
    session: AsyncSession, model: type[Row], user_id: str, ids: Sequence[str]
) -> list[Row]:
    """The user's rows among ``ids`` (read by chunks)."""
    found: list[Row] = []
    unique = list(dict.fromkeys(ids))
    for at in range(0, len(unique), _CHUNK):
        part = unique[at : at + _CHUNK]
        query: Any = select(model).where(
            model.user_id == user_id, model.id.in_(part)
        )
        found += list((await session.execute(query)).scalars())
    return found
