"""CRUD for treatments / medications (traitements)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.medical import Treatment
from app.schemas.care import TreatmentIn


async def create(
    session: AsyncSession, user_id: str, data: TreatmentIn
) -> Treatment:
    """Create a treatment for the user."""
    row = Treatment(user_id=user_id, **data.model_dump())
    session.add(row)
    await session.flush()
    return row


async def list_all(session: AsyncSession, user_id: str) -> list[Treatment]:
    """Return the user's treatments, newest first."""
    result = await session.execute(
        select(Treatment)
        .where(Treatment.user_id == user_id)
        .order_by(Treatment.created_at.desc())
    )
    return list(result.scalars().all())


async def update(
    session: AsyncSession, user_id: str, tid: str, data: TreatmentIn
) -> Treatment:
    """Replace a treatment's fields."""
    row = await get(session, user_id, tid)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    await session.flush()
    return row


async def delete(session: AsyncSession, user_id: str, tid: str) -> None:
    """Delete one of the user's treatments."""
    row = await get(session, user_id, tid)
    await session.delete(row)
    await session.flush()


async def get(session: AsyncSession, user_id: str, tid: str) -> Treatment:
    """Return the user's treatment or raise NotFound."""
    row = await session.get(Treatment, tid)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Treatment not found")
    return row
