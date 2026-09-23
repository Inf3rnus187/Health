"""Traces that are meals: a delivery or a meal bought becomes a meal.

The meal gets the order's time, vendor, items and price; the AI reads it
like any meal (nutrients, score), so the file can show what long days
cost — in money and in food quality.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import Meal
from app.models.work import Evidence
from app.services import meal_ai, meals
from app.services.timed_entries import utc

#: Trace kinds that are meals.
MEAL_KINDS = {"livraison", "repas"}


async def add_meal(session: AsyncSession, row: Evidence, items: str) -> Meal:
    """Log the meal a delivery / purchase stands for and link it."""
    vendor = row.place or row.title
    what = items or row.description or row.title or "repas"
    fields = {
        "eaten_at": utc(row.occurred_at),
        "description": f"{vendor} : {what}" if vendor else what,
        "price": row.amount,
        "vendor": vendor,
    }
    meal = await meals.create(session, row.user_id, fields, None)
    row.meal_id = meal.id
    await session.flush()
    return meal


async def read_meal(session: AsyncSession, meal: Meal) -> None:
    """Queue the AI reading of a meal logged from a trace."""
    await meal_ai.queue(session, meal)
