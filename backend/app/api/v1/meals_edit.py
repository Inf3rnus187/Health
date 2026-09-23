"""Meal journal: change, re-read or delete a meal."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import Principal, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.meal import Meal
from app.schemas.journal import MealOut, MealUpdate
from app.services import meal_ai, meals

router = APIRouter(prefix="/meals", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.put("/{meal_id}", response_model=MealOut)
async def update(
    meal_id: str, body: MealUpdate, principal: WriteDep, session: SessionDep
) -> Meal:
    """Change type, time or description, then read the meal again."""
    fields = body.model_dump(exclude_unset=True)
    meal = await meals.update(session, principal.user.id, meal_id, fields)
    await session.commit()
    await meal_ai.queue(session, meal)
    return meal


@router.post("/{meal_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze(
    meal_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Read the meal again with the current models."""
    meal = await meals.get(session, principal.user.id, meal_id)
    queued = await meal_ai.queue(session, meal)
    return {"status": "queued" if queued else "unavailable"}


@router.delete("/{meal_id}")
async def delete(
    meal_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete a meal, its photo and its nutrients."""
    await meals.delete(session, principal.user.id, meal_id)
    await session.commit()
    return {"detail": "deleted"}
