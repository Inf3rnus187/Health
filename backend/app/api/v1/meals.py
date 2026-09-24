"""Meal journal: photo + description, AI reading, nutrients."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response
from starlette.datastructures import UploadFile as Upload

from app.core.deps import Principal, ReaderDep, SessionDep
from app.core.deps_query import require_scope_flex
from app.core.errors import InvalidInputError, NotFoundError
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.models.meal import Meal
from app.schemas.journal import MealOut
from app.services import meal_ai, meal_form, meal_photo, meals

router = APIRouter(prefix="/meals", tags=["journal"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]


@router.post("", response_model=MealOut, status_code=status.HTTP_201_CREATED)
async def create(
    principal: TapDep,
    session: SessionDep,
    meal_type: Annotated[str, Form()] = "",
    eaten_at: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | str | None, File()] = None,
    photos: Annotated[list[UploadFile | str] | None, File()] = None,
    foods: Annotated[str, Form()] = "",
) -> Meal:
    """Log a meal for the health follow-up, then read it with the AI.

    Form fields: ``description``, ``file`` (the plate's photo: JPEG,
    HEIC, PNG…), and optionally ``photos`` (up to 6 more files: the box,
    the sachet, its nutrition table), ``foods`` (catalogue foods eaten,
    JSON ``[{"food_id": "…", "grams": 125}]``; a food the description
    names is found anyway), ``meal_type`` (default: from the hour) and
    ``eaten_at`` (default: now; ``2026-09-23T20:30``, with or without an
    offset, or ``23/09/2026 20:30`` — a time without offset is local).
    An empty field (an iPhone Shortcut without photo) counts as absent.

    Health only: such a meal is never a work proof and has no price. A
    meal paid for (receipt, delivery, expense report) is a proof —
    ``POST /evidence`` with ``meal=true`` — which logs its meal here too.
    """
    fields = {
        "meal_type": meal_type,
        "eaten_at": _when(eaten_at),
        "description": description,
        "foods": meal_form.portions(foods),
    }
    sent = [await _photo(f) for f in [file, *(photos or [])]]
    shots = [s for s in sent if s is not None]
    meal = await meals.create(session, principal.user.id, fields, shots)
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


#: Day-first forms a Shortcut may send besides ISO (« 23/09/2026 20:30 »).
_DAY_FIRST = ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y")


def _when(value: str) -> datetime | None:
    """A form date-time (ISO or day first, local time allowed) or None."""
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for form in _DAY_FIRST:
        try:
            return datetime.strptime(text, form)
        except ValueError:
            continue
    raise InvalidInputError(
        "eaten_at must be a date-time: 2026-09-23T20:30 or 23/09/2026 20:30"
    )


async def _photo(file: Upload | str | None) -> tuple[bytes, str] | None:
    """The photo sent, None when the field is missing or empty.

    A file without an image type (``application/octet-stream``) is still
    tried: the image decoder decides.
    """
    if not isinstance(file, Upload):
        return None
    data = await file.read()
    if not data:
        return None
    kind = file.content_type or ""
    return data, kind if kind.startswith("image/") else "image/unknown"
