"""Photo read endpoints: list, detail, analysis and comparison."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import PrincipalDep, SessionDep
from app.core.errors import NotFoundError
from app.models.photo import Photo, PhotoAnalysis
from app.schemas.photo import (
    PhotoAnalysisOut,
    PhotoComparison,
    PhotoOut,
)
from app.services import photos as svc

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("", response_model=list[PhotoOut])
async def index(
    principal: PrincipalDep,
    session: SessionDep,
    angle: Annotated[str | None, Query()] = None,
) -> list[Photo]:
    """List the caller's photos (optionally filtered by angle)."""
    return await svc.list_photos(session, principal.user.id, angle=angle)


@router.get("/compare", response_model=PhotoComparison)
async def compare(
    principal: PrincipalDep,
    session: SessionDep,
    from_id: Annotated[str, Query(alias="from")],
    to_id: Annotated[str, Query(alias="to")],
) -> PhotoComparison:
    """Return two photos with their analyses for a before/after view."""
    left = await svc.get_photo(session, principal.user.id, from_id)
    right = await svc.get_photo(session, principal.user.id, to_id)
    return PhotoComparison(
        from_photo=PhotoOut.model_validate(left),
        to_photo=PhotoOut.model_validate(right),
        from_analysis=await _analysis_out(session, left.id),
        to_analysis=await _analysis_out(session, right.id),
    )


@router.get("/{photo_id}/analysis", response_model=PhotoAnalysisOut)
async def analysis(
    photo_id: str, principal: PrincipalDep, session: SessionDep
) -> PhotoAnalysis:
    """Return the latest AI analysis for one photo."""
    await svc.get_photo(session, principal.user.id, photo_id)
    result = await svc.get_analysis(session, photo_id)
    if result is None:
        raise NotFoundError("No analysis yet")
    return result


@router.get("/{photo_id}", response_model=PhotoOut)
async def detail(
    photo_id: str, principal: PrincipalDep, session: SessionDep
) -> Photo:
    """Return one photo's metadata."""
    return await svc.get_photo(session, principal.user.id, photo_id)


async def _analysis_out(
    session: SessionDep, photo_id: str
) -> PhotoAnalysisOut | None:
    """Return a serialized analysis for a photo, if present."""
    found = await svc.get_analysis(session, photo_id)
    return PhotoAnalysisOut.model_validate(found) if found else None
