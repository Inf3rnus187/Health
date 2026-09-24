"""A meal's other photos: its pack, the nutrition label, the receipt."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import Response

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.errors import InvalidInputError
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.meal import Meal
from app.schemas.journal import MealOut
from app.services import meal_ai, meal_extra, meals

router = APIRouter(prefix="/meals", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
MOST_PHOTOS = 6


@router.post(
    "/{meal_id}/photos",
    response_model=MealOut,
    status_code=status.HTTP_201_CREATED,
)
async def add(
    meal_id: str, principal: WriteDep, session: SessionDep, file: UploadFile
) -> Meal:
    """Add a photo (the pack, its nutrition label…), then read again."""
    meal = await meals.get(session, principal.user.id, meal_id)
    if len(meal.photos or []) >= MOST_PHOTOS:
        raise InvalidInputError(f"At most {MOST_PHOTOS} more photos")
    meal_extra.add(meal, await file.read(), file.content_type or "image/")
    await session.commit()
    await meal_ai.queue(session, meal)
    return meal


@router.get("/{meal_id}/photos/{photo_id}")
async def photo(
    meal_id: str, photo_id: str, principal: ReaderDep, session: SessionDep
) -> Response:
    """One of the meal's other photos (JPEG, EXIF removed)."""
    meal = await meals.get(session, principal.user.id, meal_id)
    data = meal_extra.read(meal, photo_id)
    return Response(content=data, media_type="image/jpeg")


@router.delete("/{meal_id}/photos/{photo_id}", response_model=MealOut)
async def remove(
    meal_id: str, photo_id: str, principal: WriteDep, session: SessionDep
) -> Meal:
    """Delete one of the meal's other photos (the reading stays)."""
    meal = await meals.get(session, principal.user.id, meal_id)
    meal_extra.remove(meal, photo_id)
    await session.commit()
    return meal
