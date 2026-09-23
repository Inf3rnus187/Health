"""Meal photos: validated, EXIF-free (no GPS), resized JPEG, encrypted."""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.errors import InvalidInputError
from app.models.meal import Meal
from app.services import imaging, photo_storage


def save(user_id: str, meal_id: str, data: bytes, content_type: str) -> str:
    """Store the photo as a clean JPEG; return its path."""
    if not content_type.startswith("image/"):
        raise InvalidInputError("The meal photo must be an image")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise InvalidInputError("Image exceeds the size limit")
    try:
        clean = imaging.normalize_bytes(data)
    except Exception as exc:  # noqa: BLE001 - any decoding failure
        raise InvalidInputError("Unreadable image") from exc
    path = photo_storage.user_dir(user_id) / f"meal_{meal_id}.jpg"
    photo_storage.write_bytes(path, clean)
    return str(path)


def read(meal: Meal) -> bytes | None:
    """The meal's photo (JPEG), if any."""
    if not meal.photo_path or not Path(meal.photo_path).exists():
        return None
    return photo_storage.read_bytes(Path(meal.photo_path))


def drop(meal: Meal) -> None:
    """Delete the meal's photo file, if any."""
    if meal.photo_path:
        Path(meal.photo_path).unlink(missing_ok=True)
