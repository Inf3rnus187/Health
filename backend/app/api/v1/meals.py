"""Meal journal: photo + description, AI reading, nutrients."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import Principal, ReaderDep, SessionDep
from app.core.deps_query import require_scope_flex
from app.core.errors import InvalidInputError, NotFoundError
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.models.meal import Meal
from app.schemas.journal import MealOut
from app.services import meal_ai, meal_photo, meals

router = APIRouter(prefix="/meals", tags=["journal"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]


@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED)
async def create(
    principal: TapDep,
    session: SessionDep,
    meal_type: Annotated[str, Form()] = "lunch",
    eaten_at: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    file: UploadFile | None = None,
) -> Meal:
    """Log a meal (photo and/or description), then read it with the AI."""
    fields = {
        "meal_type": meal_type,
        "eaten_at": _when(eaten_at),
        "description": description,
    }
    photo = None
    if file is not None and file.filename:
        photo = (await file.read(), file.content_type or "")
    meal = await meals.create(session, principal.user.id, fields, photo)
    await session.commit()
    await meal_ai.queue(session, meal)
    return meal


@router.get("", response_model=list[MealOut])
async def index(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[Meal]:
    """Meals between two days (default: the last 7 days), newest first."""
    last = end or utcnow().date()
    first = start or last - timedelta(days=6)
    return await meals.list_meals(session, principal.user.id, first, last)


@router.get("/{meal_id}", response_model=MealOut)
async def detail(
    meal_id: str, principal: ReaderDep, session: SessionDep
) -> Meal:
    """One meal with its reading."""
    return await meals.get(session, principal.user.id, meal_id)


@router.get("/{meal_id}/photo")
async def photo(
    meal_id: str, principal: ReaderDep, session: SessionDep
) -> Response:
    """The meal's photo (JPEG, EXIF removed)."""
    meal = await meals.get(session, principal.user.id, meal_id)
    data = meal_photo.read(meal)
    if data is None:
        raise NotFoundError("No photo for this meal")
    return Response(content=data, media_type="image/jpeg")


def _when(value: str) -> datetime | None:
    """A form date-time (ISO, local time allowed) or None."""
    if not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise InvalidInputError("eaten_at must be an ISO date-time") from exc
