"""A meal's other photos: its pack, the nutrition label, the receipt.

Kept with more pixels than the plate's photo (2048) so a label's small
print stays readable by the vision model; cleaned and encrypted like
every photo, in the user's media folder.
"""

from __future__ import annotations

from pathlib import Path

from app.core.errors import NotFoundError
from app.models.base import new_uuid
from app.models.meal import Meal
from app.services import imaging, meal_photo, photo_storage

_SIDE = 2048


def add(meal: Meal, data: bytes, content_type: str) -> str:
    """Store one more photo (a pack, a label…); return its id."""
    jpeg = meal_photo.clean(
        data, content_type, lambda d: imaging.normalize_bytes(d, _SIDE)
    )
    photo_id = new_uuid()
    path = (
        photo_storage.user_dir(meal.user_id) / f"meal_{meal.id}_{photo_id}.jpg"
    )
    photo_storage.write_bytes(path, jpeg)
    meal.photos = [*(meal.photos or []), {"id": photo_id, "path": str(path)}]
    return photo_id


def read(meal: Meal, photo_id: str) -> bytes:
    """One of the meal's other photos (JPEG)."""
    found = next(
        (p for p in meal.photos or [] if p.get("id") == photo_id), None
    )
    if found is None or not Path(str(found["path"])).exists():
        raise NotFoundError("Photo not found")
    return photo_storage.read_bytes(Path(str(found["path"])))


def remove(meal: Meal, photo_id: str) -> None:
    """Delete one of the meal's other photos."""
    found = [p for p in meal.photos or [] if p.get("id") == photo_id]
    if not found:
        raise NotFoundError("Photo not found")
    Path(str(found[0]["path"])).unlink(missing_ok=True)
    meal.photos = [p for p in meal.photos if p.get("id") != photo_id]


def read_all(meal: Meal) -> list[bytes]:
    """Every photo of the meal: the plate's first, then the others."""
    out = [data] if (data := meal_photo.read(meal)) is not None else []
    for photo in meal.photos or []:
        path = Path(str(photo.get("path")))
        if path.exists():
            out.append(photo_storage.read_bytes(path))
    return out
