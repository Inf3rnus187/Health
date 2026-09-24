"""A food's photos (pack, label) and reading a label with the AI."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, UploadFile, status
from fastapi.responses import Response

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.food import FoodOut
from app.services import food_label, food_photos, foods

router = APIRouter(prefix="/foods", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("/read-label")
async def read_label(principal: WriteDep, file: UploadFile) -> dict[str, Any]:
    """Read a pack or its nutrition table with the vision model.

    A proposal to check, nothing is saved: ``name``, ``brand``,
    ``package_g`` (net weight) and ``per_100g`` (only plausible values;
    sodium from salt when only salt is printed).
    """
    del principal
    return await food_label.read(await file.read())


@router.post(
    "/{food_id}/photos",
    response_model=FoodOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_photo(
    food_id: str,
    principal: WriteDep,
    session: SessionDep,
    file: UploadFile,
    kind: Annotated[str, Form(pattern="^(pack|label)$")] = "pack",
) -> FoodOut:
    """Add a photo: ``kind`` = ``pack`` (the box) or ``label`` (values)."""
    food = await foods.get(session, principal.user.id, food_id)
    data = await file.read()
    food_photos.add(food, data, file.content_type or "", kind)
    await session.commit()
    return FoodOut.of(food)


@router.get("/{food_id}/photos/{photo_id}")
async def photo(
    food_id: str, photo_id: str, principal: ReaderDep, session: SessionDep
) -> Response:
    """One of the food's photos (JPEG, EXIF removed)."""
    food = await foods.get(session, principal.user.id, food_id)
    return Response(
        content=food_photos.read(food, photo_id), media_type="image/jpeg"
    )


@router.delete("/{food_id}/photos/{photo_id}", response_model=FoodOut)
async def remove_photo(
    food_id: str, photo_id: str, principal: WriteDep, session: SessionDep
) -> FoodOut:
    """Delete one of the food's photos."""
    food = await foods.get(session, principal.user.id, food_id)
    food_photos.remove(food, photo_id)
    await session.commit()
    return FoodOut.of(food)
