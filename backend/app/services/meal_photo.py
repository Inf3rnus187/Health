"""Meal photos: validated, EXIF-free (no GPS), resized JPEG, encrypted.

The plate's photo (``photo_path``), and more photos (the pack, its
nutrition label…) in ``meal.photos``, kept with more pixels so a label's
small print stays readable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.errors import InvalidInputError
from app.models.meal import Meal
from app.services import imaging, photo_storage


def save(user_id: str, meal_id: str, data: bytes, content_type: str) -> str:
    """Store the photo as a clean JPEG; return its path."""
    clean_jpeg = clean(data, content_type, imaging.normalize_bytes)
    path = photo_storage.user_dir(user_id) / f"meal_{meal_id}.jpg"
    photo_storage.write_bytes(path, clean_jpeg)
    return str(path)


def clean(data: bytes, content_type: str, normalize: Any) -> bytes:
    """A decoded, EXIF-free JPEG, or why the upload is refused."""
    if not content_type.startswith("image/"):
        raise InvalidInputError("The meal photo must be an image")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise InvalidInputError("Image exceeds the size limit")
    try:
        return bytes(normalize(data))
    except Exception as exc:  # noqa: BLE001 - any decoding failure
        raise InvalidInputError("Unreadable image") from exc


def read(meal: Meal) -> bytes | None:
    """The meal's photo (JPEG), if any."""
    if not meal.photo_path or not Path(meal.photo_path).exists():
        return None
    return photo_storage.read_bytes(Path(meal.photo_path))


def drop(meal: Meal) -> None:
    """Delete the meal's photo files, if any."""
    drop_plate(meal)
    for photo in meal.photos or []:
        Path(str(photo.get("path"))).unlink(missing_ok=True)


def drop_plate(meal: Meal) -> None:
    """Delete the plate's photo (the other photos stay)."""
    if meal.photo_path:
        Path(meal.photo_path).unlink(missing_ok=True)
    meal.photo_path = None
