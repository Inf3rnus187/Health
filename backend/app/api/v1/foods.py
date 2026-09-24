"""The foods eaten often: a sheet filled once (label, package weight).

A meal that names one of them (or picks it) is read with its label
values instead of an estimate.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.food import FoodIn, FoodOut
from app.services import foods

router = APIRouter(prefix="/foods", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.get("", response_model=list[FoodOut])
async def index(principal: ReaderDep, session: SessionDep) -> list[FoodOut]:
    """The user's foods, by name."""
    found = await foods.list_foods(session, principal.user.id)
    return [FoodOut.of(food) for food in found]


@router.post("", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: FoodIn, principal: WriteDep, session: SessionDep
) -> FoodOut:
    """Add a food: name, brand, aliases, package weight, values per 100 g.

    ``aliases``: other ways of naming it in a meal, comma separated
    (« riz uncle bens, riz méditerranéen »). The photos (pack, label) go
    through ``POST /foods/{id}/photos``.
    """
    food = await foods.create(session, principal.user.id, body)
    await session.commit()
    return FoodOut.of(food)


@router.get("/{food_id}", response_model=FoodOut)
async def detail(
    food_id: str, principal: ReaderDep, session: SessionDep
) -> FoodOut:
    """One food."""
    return FoodOut.of(await foods.get(session, principal.user.id, food_id))


@router.put("/{food_id}", response_model=FoodOut)
async def update(
    food_id: str, body: FoodIn, principal: WriteDep, session: SessionDep
) -> FoodOut:
    """Change a food (every field; the meals already read keep theirs)."""
    food = await foods.get(session, principal.user.id, food_id)
    await foods.update(session, food, body)
    await session.commit()
    return FoodOut.of(food)


@router.delete("/{food_id}")
async def delete(
    food_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete a food and its photos."""
    food = await foods.get(session, principal.user.id, food_id)
    await foods.delete(session, food)
    await session.commit()
    return {"detail": "deleted"}
