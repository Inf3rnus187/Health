"""A meal's other photos: its pack, the nutrition label, the receipt."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.errors import InvalidInputError
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.meal import Meal
from app.schemas.journal import MealOut
from app.services import meal_ai, meal_extra, meal_photo, meals

router = APIRouter(prefix="/meals", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]
MOST_PHOTOS = 6
#: ``read=false``: change several photos, then read the meal once.
ReadQuery = Annotated[bool, Query(alias="read")]


@router.post(
    "/{meal_id}/photos",
    response_model=MealOut,
    status_code=status.HTTP_201_CREATED,
)
async def add(
    meal_id: str,
    principal: WriteDep,
    session: SessionDep,
    file: UploadFile,
    reread: ReadQuery = True,
) -> Meal:
    """Add a photo afterwards, then read the meal again.

    A meal without a photo gets it as the plate's; otherwise it joins the
    others (the pack, its nutrition label…, 6 at most). ``read=false``
    skips the new reading (several changes, then ``PUT`` or
    ``/analyze``).
    """
    meal = await meals.get(session, principal.user.id, meal_id)
    data, kind = await file.read(), file.content_type or "image/"
    if not meal.photo_path:
        meal.photo_path = meal_photo.save(meal.user_id, meal.id, data, kind)
    elif len(meal.photos or []) >= MOST_PHOTOS:
        raise InvalidInputError(f"At most {MOST_PHOTOS} more photos")
    else:
        meal_extra.add(meal, data, kind)
    await session.commit()
    if reread:
        await meal_ai.queue(session, meal)
    return meal


@router.delete("/{meal_id}/photo", response_model=MealOut)
async def remove_plate(
    meal_id: str,
    principal: WriteDep,
    session: SessionDep,
    reread: ReadQuery = True,
) -> Meal:
    """Delete the plate's photo (the other photos stay), read again."""
    meal = await meals.get(session, principal.user.id, meal_id)
    meal_photo.drop_plate(meal)
    await session.commit()
    if reread:
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
    meal_id: str,
    photo_id: str,
    principal: WriteDep,
    session: SessionDep,
    reread: ReadQuery = True,
) -> Meal:
    """Delete one of the meal's other photos, then read it again."""
    meal = await meals.get(session, principal.user.id, meal_id)
    meal_extra.remove(meal, photo_id)
    await session.commit()
    if reread:
        await meal_ai.queue(session, meal)
    return meal
