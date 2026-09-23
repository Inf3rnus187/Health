"""The meal journal: when, which meal, what was eaten, the photo.

Apple Health records nutrients but no meal (no type, no description,
no photo), so meals live here; their AI reading (:mod:`meal_ai`) writes
the estimated nutrients into the same nutrition metrics as Apple.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError, NotFoundError
from app.models.base import new_uuid, utcnow
from app.models.meal import Meal
from app.services import meal_nutrients, meal_photo
from app.services.daily_rollup import user_zone
from app.services.timed_entries import day_bounds, utc

#: Meal type → French label.
TYPES = {
    "breakfast": "Petit-déjeuner",
    "lunch": "Déjeuner",
    "dinner": "Dîner",
    "snack": "Collation",
}
_DESCRIPTION_MAX = 2000
#: Default meal by local hour (before 10:30 breakfast… after 18:00 dinner).
_MEAL_HOURS = ((10.5, "breakfast"), (15.0, "lunch"), (18.0, "snack"))


async def create(
    session: AsyncSession,
    user_id: str,
    fields: dict[str, Any],
    photo: tuple[bytes, str] | None,
) -> Meal:
    """Record a meal (``fields``: meal_type, eaten_at, description)."""
    meal = Meal(id=new_uuid(), user_id=user_id)
    await _apply(session, meal, fields)
    if photo is not None:
        meal.photo_path = meal_photo.save(user_id, meal.id, *photo)
    if not meal.description and not meal.photo_path:
        raise InvalidInputError("Describe the meal or add a photo")
    session.add(meal)
    await session.flush()
    return meal


async def list_meals(
    session: AsyncSession, user_id: str, start: date, end: date
) -> list[Meal]:
    """The user's meals between two local days, newest first."""
    tz = await user_zone(session, user_id)
    low = day_bounds(start, tz)[0]
    high = day_bounds(end, tz)[1]
    result = await session.execute(
        select(Meal)
        .where(
            Meal.user_id == user_id,
            Meal.eaten_at >= low,
            Meal.eaten_at < high,
        )
        .order_by(Meal.eaten_at.desc())
    )
    return list(result.scalars().all())


async def get(session: AsyncSession, user_id: str, meal_id: str) -> Meal:
    """One of the user's meals, or NotFound."""
    meal = await session.get(Meal, meal_id)
    if meal is None or meal.user_id != user_id:
        raise NotFoundError("Meal not found")
    return meal


async def update(
    session: AsyncSession, user_id: str, meal_id: str, fields: dict[str, Any]
) -> Meal:
    """Change a meal's type, time or description (its nutrients move)."""
    meal = await get(session, user_id, meal_id)
    await meal_nutrients.clear(session, meal)
    await _apply(session, meal, fields)
    await session.flush()
    return meal


async def delete(session: AsyncSession, user_id: str, meal_id: str) -> None:
    """Delete a meal, its photo and its nutrients."""
    meal = await get(session, user_id, meal_id)
    await meal_nutrients.clear(session, meal)
    meal_photo.drop(meal)
    await session.delete(meal)
    await session.flush()


async def _apply(
    session: AsyncSession, meal: Meal, fields: dict[str, Any]
) -> None:
    """Validate and set type, time and description."""
    zone = await user_zone(session, meal.user_id)
    stored = utc(meal.eaten_at) if meal.eaten_at else None
    eaten = fields.get("eaten_at") or stored or utcnow()
    if eaten.tzinfo is None:  # a local time typed in a form
        eaten = eaten.replace(tzinfo=zone)
    local = utc(eaten).astimezone(zone)
    kind = fields.get("meal_type") or meal.meal_type or _meal_of(local)
    if kind not in TYPES:
        raise InvalidInputError(f"meal_type must be one of {sorted(TYPES)}")
    meal.meal_type = kind
    meal.date_key = local.date()
    meal.eaten_at = utc(eaten)
    text = fields.get("description")
    if text is not None:
        meal.description = str(text).strip()[:_DESCRIPTION_MAX]
    if "price" in fields:
        meal.price = fields["price"]
    if fields.get("vendor") is not None:
        meal.vendor = str(fields["vendor"]).strip()[:120]


def _meal_of(local: datetime) -> str:
    """The meal of a local time, as the web form proposes it."""
    hour = local.hour + local.minute / 60
    return next((kind for end, kind in _MEAL_HOURS if hour < end), "dinner")
