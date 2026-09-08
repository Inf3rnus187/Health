"""CRUD for automations (trigger → action rules, §7.2)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.automation import Automation
from app.schemas.automation import AutomationCreate, AutomationUpdate


async def create_automation(
    session: AsyncSession, user_id: str, data: AutomationCreate
) -> Automation:
    """Create an automation for a user."""
    automation = Automation(
        user_id=user_id,
        name=data.name,
        trigger=data.trigger,
        action=data.action,
        is_active=data.is_active,
    )
    session.add(automation)
    await session.flush()
    return automation


async def list_automations(
    session: AsyncSession, user_id: str
) -> list[Automation]:
    """Return the user's automations, newest first."""
    result = await session.execute(
        select(Automation)
        .where(Automation.user_id == user_id)
        .order_by(Automation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_automation(
    session: AsyncSession, user_id: str, automation_id: str
) -> Automation:
    """Return one of the user's automations or raise NotFound."""
    automation = await session.get(Automation, automation_id)
    if automation is None or automation.user_id != user_id:
        raise NotFoundError("Automation not found")
    return automation


async def update_automation(
    session: AsyncSession,
    user_id: str,
    automation_id: str,
    data: AutomationUpdate,
) -> Automation:
    """Apply a partial update to an automation."""
    automation = await get_automation(session, user_id, automation_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(automation, field, value)
    await session.flush()
    return automation


async def delete_automation(
    session: AsyncSession, user_id: str, automation_id: str
) -> None:
    """Delete one of the user's automations."""
    automation = await get_automation(session, user_id, automation_id)
    await session.delete(automation)
    await session.flush()
