"""CRUD for declared conditions (maladies)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.medical import Condition
from app.schemas.care import ConditionIn


async def create(
    session: AsyncSession, user_id: str, data: ConditionIn
) -> Condition:
    """Create a condition for the user."""
    row = Condition(user_id=user_id, **data.model_dump())
    session.add(row)
    await session.flush()
    return row


async def list_all(session: AsyncSession, user_id: str) -> list[Condition]:
    """Return the user's conditions, newest first."""
    result = await session.execute(
        select(Condition)
        .where(Condition.user_id == user_id)
        .order_by(Condition.created_at.desc())
    )
    return list(result.scalars().all())


async def update(
    session: AsyncSession, user_id: str, cid: str, data: ConditionIn
) -> Condition:
    """Replace a condition's fields."""
    row = await _get(session, user_id, cid)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    await session.flush()
    return row


async def delete(session: AsyncSession, user_id: str, cid: str) -> None:
    """Delete one of the user's conditions."""
    row = await _get(session, user_id, cid)
    await session.delete(row)
    await session.flush()


async def _get(session: AsyncSession, user_id: str, cid: str) -> Condition:
    """Return the user's condition or raise NotFound."""
    row = await session.get(Condition, cid)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Condition not found")
    return row
