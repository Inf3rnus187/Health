"""Photos of a food: its pack and its nutrition label.

Cleaned like every photo (EXIF and GPS removed), encrypted when the hub
encrypts, in the user's own media folder; a label keeps more pixels
(2048) so its small print stays readable.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.errors import InvalidInputError, NotFoundError
from app.models.base import new_uuid
from app.models.food import Food
from app.services import imaging, photo_storage

KINDS = ("pack", "label")
_LABEL_SIDE = 2048


def add(food: Food, data: bytes, content_type: str, kind: str) -> str:
    """Store one photo of ``food``; return its id."""
    if kind not in KINDS:
        raise InvalidInputError(f"kind must be one of {list(KINDS)}")
    if not data:
        raise InvalidInputError("Empty photo")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise InvalidInputError("Image exceeds the size limit")
    try:
        clean = imaging.normalize_bytes(data, _LABEL_SIDE)
    except Exception as exc:  # noqa: BLE001 - any decoding failure
        raise InvalidInputError("Unreadable image") from exc
    del content_type  # the decoder decides (HEIC, JPEG, PNG…)
    photo_id = new_uuid()
    path = photo_storage.user_dir(food.user_id) / f"food_{photo_id}.jpg"
    photo_storage.write_bytes(path, clean)
    food.photos = [
        *food.photos,
        {"id": photo_id, "kind": kind, "path": str(path)},
    ]
    return photo_id


def read(food: Food, photo_id: str) -> bytes:
    """One of the food's photos (JPEG)."""
    path = _path(food, photo_id)
    if not path.exists():
        raise NotFoundError("Photo not found")
    return photo_storage.read_bytes(path)


def remove(food: Food, photo_id: str) -> None:
    """Delete one of the food's photos."""
    _path(food, photo_id).unlink(missing_ok=True)
    food.photos = [p for p in food.photos if p.get("id") != photo_id]


def drop_all(food: Food) -> None:
    """Delete every photo of the food (it is being deleted)."""
    for photo in food.photos:
        Path(str(photo.get("path"))).unlink(missing_ok=True)


def _path(food: Food, photo_id: str) -> Path:
    """Where one of the food's photos is stored."""
    found = next((p for p in food.photos if p.get("id") == photo_id), None)
    if found is None:
        raise NotFoundError("Photo not found")
    return Path(str(found["path"]))
