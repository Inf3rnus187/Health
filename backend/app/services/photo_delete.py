"""Delete photos: their DB rows, analyses and on-disk files."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo, PhotoAnalysis
from app.services import photos as svc


def _remove_files(photo: Photo) -> None:
    """Unlink a photo's original and normalized files if present."""
    for path in (photo.original_path, photo.normalized_path):
        if path:
            Path(path).unlink(missing_ok=True)


async def delete_one(
    session: AsyncSession, user_id: str, photo_id: str
) -> None:
    """Delete one of the user's photos (files + analyses + row)."""
    photo = await svc.get_photo(session, user_id, photo_id)
    _remove_files(photo)
    await session.execute(
        sql_delete(PhotoAnalysis).where(PhotoAnalysis.photo_id == photo.id)
    )
    await session.delete(photo)
    await session.flush()


async def delete_all(session: AsyncSession, user_id: str) -> int:
    """Delete every photo of the user; return how many were removed."""
    rows = await svc.list_photos(session, user_id)
    for photo in rows:
        _remove_files(photo)
    ids = [photo.id for photo in rows]
    if ids:
        await session.execute(
            sql_delete(PhotoAnalysis).where(PhotoAnalysis.photo_id.in_(ids))
        )
        await session.execute(sql_delete(Photo).where(Photo.id.in_(ids)))
    await session.flush()
    return len(ids)
