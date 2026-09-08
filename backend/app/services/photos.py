"""Persistence and queries for photos and their analyses."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.photo import Photo, PhotoAnalysis


async def create_photo(
    session: AsyncSession,
    user_id: str,
    *,
    angle: str,
    date_key: date,
    taken_at: datetime,
    original_path: str,
    linked_weight: float | None = None,
) -> Photo:
    """Create a received photo row awaiting the pipeline."""
    photo = Photo(
        user_id=user_id,
        angle=angle,
        date_key=date_key,
        taken_at=taken_at,
        original_path=original_path,
        linked_weight=linked_weight,
        status="received",
    )
    session.add(photo)
    await session.flush()
    return photo


async def list_photos(
    session: AsyncSession, user_id: str, *, angle: str | None = None
) -> list[Photo]:
    """Return the user's photos, newest first, optionally by angle."""
    stmt = select(Photo).where(Photo.user_id == user_id)
    if angle is not None:
        stmt = stmt.where(Photo.angle == angle)
    result = await session.execute(stmt.order_by(Photo.taken_at.desc()))
    return list(result.scalars().all())


async def get_photo(
    session: AsyncSession, user_id: str, photo_id: str
) -> Photo:
    """Return one of the user's photos or raise :class:`NotFoundError`."""
    photo = await session.get(Photo, photo_id)
    if photo is None or photo.user_id != user_id:
        raise NotFoundError("Photo not found")
    return photo


async def get_analysis(
    session: AsyncSession, photo_id: str
) -> PhotoAnalysis | None:
    """Return the latest analysis for a photo, if any."""
    result = await session.execute(
        select(PhotoAnalysis)
        .where(PhotoAnalysis.photo_id == photo_id)
        .order_by(PhotoAnalysis.created_at.desc())
    )
    return result.scalars().first()


async def latest_before(
    session: AsyncSession, user_id: str, angle: str, before: datetime
) -> Photo | None:
    """Return the previous same-angle photo, for comparison."""
    result = await session.execute(
        select(Photo)
        .where(
            Photo.user_id == user_id,
            Photo.angle == angle,
            Photo.taken_at < before,
        )
        .order_by(Photo.taken_at.desc())
    )
    return result.scalars().first()
