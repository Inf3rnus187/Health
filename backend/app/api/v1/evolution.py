"""Long-term evolution: photo trends, validated markers, re-analysis."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.deps import (
    Principal,
    ReaderDep,
    SessionDep,
    UserDep,
    require_scope,
)
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.evolution import ProfileIn
from app.services import metabolic, photo_trend
from app.services import photos as photo_svc
from app.workers.queue import enqueue_many

router = APIRouter(prefix="/evolution", tags=["evolution"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.get("/trend")
async def trend(principal: ReaderDep, session: SessionDep) -> dict[str, Any]:
    """Per-angle, per-criterion long-term photo score evolution."""
    return await photo_trend.trend(session, principal.user.id)


@router.get("/markers")
async def markers(principal: ReaderDep, session: SessionDep) -> dict[str, Any]:
    """Validated metabolic / liver markers from the latest data."""
    return await metabolic.markers(session, principal.user.id)


@router.post("/profile")
async def profile(
    body: ProfileIn, principal: WriteDep, session: SessionDep
) -> dict[str, Any]:
    """Record waist / height / birth year, then return the markers."""
    fields = body.model_dump(exclude_none=True, exclude={"date_key"})
    day = body.date_key or date.today()
    await metabolic.save_profile(session, principal.user.id, fields, day)
    await session.commit()
    return await metabolic.markers(session, principal.user.id)


@router.post("/reanalyze-all", status_code=status.HTTP_202_ACCEPTED)
async def reanalyze_all(
    principal: UserDep, session: SessionDep
) -> dict[str, int]:
    """Re-run the current method over every photo, oldest first."""
    photos = await photo_svc.list_photos(session, principal.user.id)
    ordered = sorted(photos, key=lambda photo: photo.taken_at)
    queued = await enqueue_many("analyze_photo", [(p.id,) for p in ordered])
    return {"queued": queued}
