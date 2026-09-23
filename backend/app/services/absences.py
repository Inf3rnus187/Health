"""Absences: sick leave, work accident, occupational disease, holidays."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.base import new_uuid
from app.models.work import Absence

#: Kind → French label.
KINDS = {
    "arret_maladie": "Arrêt maladie",
    "accident_travail": "Accident du travail",
    "maladie_pro": "Maladie professionnelle",
    "conge": "Congés",
    "repos": "Repos (RTT, récupération)",
    "autre": "Autre absence",
}


async def list_absences(
    session: AsyncSession,
    user_id: str,
    first: date | None = None,
    last: date | None = None,
) -> list[Absence]:
    """Absences overlapping ``first``..``last`` (all by default), in order."""
    query = select(Absence).where(Absence.user_id == user_id)
    if first is not None:
        query = query.where(Absence.end_date >= first)
    if last is not None:
        query = query.where(Absence.start_date <= last)
    rows = await session.execute(query.order_by(Absence.start_date))
    return list(rows.scalars())


async def save(
    session: AsyncSession,
    user_id: str,
    fields: dict[str, Any],
    absence_id: str | None = None,
) -> Absence:
    """Create an absence, or replace one (``absence_id``)."""
    row = (
        await get(session, user_id, absence_id)
        if absence_id
        else Absence(id=new_uuid(), user_id=user_id)
    )
    for key, value in fields.items():
        setattr(row, key, value)
    session.add(row)
    await session.flush()
    return row


async def get(session: AsyncSession, user_id: str, absence_id: str) -> Absence:
    """One of the user's absences or NotFoundError."""
    row = await session.get(Absence, absence_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Absence not found")
    return row


async def delete(session: AsyncSession, user_id: str, absence_id: str) -> None:
    """Delete an absence (its evidence stays, unlinked)."""
    await session.delete(await get(session, user_id, absence_id))
    await session.flush()
