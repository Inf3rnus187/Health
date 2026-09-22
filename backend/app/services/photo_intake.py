"""Validate and store a photo upload, creating its DB row (§8.1, §12.1)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InvalidInputError
from app.models.base import new_uuid, utcnow
from app.models.photo import Photo
from app.services import photo_storage

_ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
_ANGLES = {"face", "profil", "dos"}


def _validate(content_type: str, angle: str, data: bytes) -> str:
    """Validate type/angle/size and return the file extension."""
    ext = _ALLOWED.get(content_type)
    if ext is None:
        raise InvalidInputError("Unsupported image type")
    if angle not in _ANGLES:
        raise InvalidInputError("angle must be face, profil or dos")
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise InvalidInputError("Image exceeds the size limit")
    return ext


async def intake(
    session: AsyncSession,
    user_id: str,
    *,
    content_type: str,
    data: bytes,
    angle: str,
    date_key: date | None,
    weight: float | None,
) -> Photo:
    """Persist the upload and its received-status row."""
    ext = _validate(content_type, angle, data)
    photo_id = new_uuid()
    path = photo_storage.original_path(user_id, photo_id, angle, ext)
    photo_storage.write_bytes(path, data)
    photo = Photo(
        id=photo_id,
        user_id=user_id,
        angle=angle,
        date_key=date_key or utcnow().date(),
        taken_at=utcnow(),
        original_path=str(path),
        linked_weight=weight,
        status="received",
    )
    session.add(photo)
    await session.flush()
    return photo
