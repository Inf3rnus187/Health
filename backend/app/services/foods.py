"""A user's foods: the boxes and sachets eaten often, their label once.

Each belongs to its user (every query filters on it); deleting one
deletes its photos. The label values are checked by the schema (per
100 g: energy ≤ 900 kcal, a macro ≤ 100 g, sodium ≤ 40 g).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.food import Food
from app.schemas.food import FoodIn
from app.services import food_photos


async def list_foods(session: AsyncSession, user_id: str) -> list[Food]:
    """The user's foods, by name, then the smaller package first."""
    rows = await session.execute(
        select(Food)
        .where(Food.user_id == user_id)
        .order_by(Food.name, Food.package_g)
    )
    return list(rows.scalars())


async def get(session: AsyncSession, user_id: str, food_id: str) -> Food:
    """One of the user's foods (404 for anyone else's)."""
    food = await session.get(Food, food_id)
    if food is None or food.user_id != user_id:
        raise NotFoundError("Food not found")
    return food


async def create(session: AsyncSession, user_id: str, data: FoodIn) -> Food:
    """Add a food to the user's catalogue."""
    food = Food(user_id=user_id, photos=[], **_fields(data))
    session.add(food)
    await session.flush()
    return food


async def update(session: AsyncSession, food: Food, data: FoodIn) -> Food:
    """Change a food's name, package, values or note."""
    for key, value in _fields(data).items():
        setattr(food, key, value)
    await session.flush()
    return food


async def delete(session: AsyncSession, food: Food) -> None:
    """Delete a food and its photos (meals keep their own reading)."""
    food_photos.drop_all(food)
    await session.delete(food)
    await session.flush()


def _fields(data: FoodIn) -> dict[str, Any]:
    """The stored fields (label values without the blanks)."""
    values = {
        k: v for k, v in data.per_100g.model_dump().items() if v is not None
    }
    return {
        "name": data.name.strip(),
        "brand": data.brand.strip(),
        "aliases": data.aliases.strip(),
        "package_g": data.package_g,
        "unit_name": data.unit_name.strip(),
        "unit_g": data.unit_g,
        "portion_g": data.portion_g,
        "per_100g": values,
        "note": data.note.strip(),
        "source": data.source.strip(),
        "barcode": data.barcode,
        "product_info": data.product_info.model_dump()
        if data.product_info
        else None,
    }
