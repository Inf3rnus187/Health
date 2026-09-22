"""Blinded, counterbalanced paired comparison of two same-angle photos.

Both photos are placed in ONE labelled image (1 and 2) so any vision
model sees them together. The model is never told which one is older
(no expectation bias), and each pair is asked twice with the order
swapped: position bias cancels in ``(forward - backward) / 2`` and a
pair whose two answers do not mirror each other is flagged unreliable.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ollama
from app.models.photo import Photo
from app.services import photo_method, photo_quality, photo_storage

_SIDE = 640
_GAP = 16


class Reference(NamedTuple):
    """A reference photo chosen for one comparison horizon."""

    horizon: str
    label: str
    photo: Photo
    data: bytes


def compose(first: bytes, second: bytes) -> tuple[bytes, bool]:
    """Stack two photos (labelled 1, 2); vertical when they are wide."""
    one, two = _open(first), _open(second)
    vertical = one.width > one.height
    one, two = _fit(one, vertical), _fit(two, vertical)
    if vertical:
        size = (max(one.width, two.width), one.height + _GAP + two.height)
        spot = (0, one.height + _GAP)
    else:
        size = (one.width + _GAP + two.width, max(one.height, two.height))
        spot = (one.width + _GAP, 0)
    canvas = Image.new("RGB", size, (255, 255, 255))
    canvas.paste(one, (0, 0))
    canvas.paste(two, spot)
    _label(canvas, (0, 0), "1")
    _label(canvas, spot, "2")
    out = io.BytesIO()
    canvas.save(out, format="JPEG", quality=90)
    return out.getvalue(), vertical


async def compare(angle: str, older: bytes, newer: bytes) -> dict[str, Any]:
    """Return per-criterion deltas of ``newer`` vs ``older`` (-2..2)."""
    forward = await _ask(angle, older, newer)
    backward = await _ask(angle, newer, older)
    deltas: dict[str, float] = {}
    consistent: dict[str, bool] = {}
    for key, ahead in forward.items():
        behind = backward.get(key)
        if behind is None:
            continue
        deltas[key] = (ahead - behind) / 2
        consistent[key] = abs(ahead + behind) <= 1
    return {"deltas": deltas, "consistent": consistent}


async def references(session: AsyncSession, photo: Photo) -> list[Reference]:
    """Pick the baseline and the ~7/30/90-day references for ``photo``."""
    earlier = await _earlier(session, photo)
    chosen: list[Reference] = []
    base = _first_usable(earlier)
    if base is not None:
        chosen.append(Reference("baseline", "vs référence (J0)", *base))
    for horizon in photo_method.HORIZONS:
        target = date.fromordinal(photo.date_key.toordinal() - horizon.days)
        near = sorted(
            (p for p in earlier if _gap(p, target) <= horizon.tolerance),
            key=lambda p: _gap(p, target),
        )
        found = _first_usable(near)
        used = {ref.photo.id for ref in chosen}
        if found is not None and found[0].id not in used:
            chosen.append(Reference(horizon.key, horizon.label, *found))
    return chosen


async def _ask(angle: str, first: bytes, second: bytes) -> dict[str, int]:
    """Ask the model how photo 2 differs from photo 1, per criterion."""
    image, vertical = compose(first, second)
    prompt = photo_method.paired_prompt(angle, vertical=vertical)
    raw = await ollama.vision_json(prompt, image)
    return photo_method.read_scores(raw, angle, low=-2, high=2)


async def _earlier(session: AsyncSession, photo: Photo) -> list[Photo]:
    """Same-user, same-angle normalized photos from earlier days."""
    result = await session.execute(
        select(Photo)
        .where(
            Photo.user_id == photo.user_id,
            Photo.angle == photo.angle,
            Photo.date_key < photo.date_key,
            Photo.normalized_path.is_not(None),
        )
        .order_by(Photo.date_key, Photo.taken_at)
    )
    return list(result.scalars().all())


def _first_usable(candidates: list[Photo]) -> tuple[Photo, bytes] | None:
    """Return the first candidate whose image passes quality control."""
    for candidate in candidates:
        data = _usable(candidate)
        if data is not None:
            return candidate, data
    return None


def _usable(photo: Photo) -> bytes | None:
    """Return a photo's normalized bytes if readable and good enough."""
    try:
        data = photo_storage.read_bytes(Path(photo.normalized_path or ""))
        return data if photo_quality.assess(data)["ok"] else None
    except Exception:  # noqa: BLE001 - a broken file is just skipped
        return None


def _gap(photo: Photo, target: date) -> int:
    """Distance in days between a photo and a target day."""
    return abs((photo.date_key - target).days)


def _open(data: bytes) -> Image.Image:
    """Decode an image as RGB."""
    with Image.open(io.BytesIO(data)) as img:
        rgb: Image.Image = img.convert("RGB")
    return rgb


def _fit(img: Image.Image, vertical: bool) -> Image.Image:
    """Scale to a common width (stacked) or height (side by side)."""
    if vertical:
        size = (_SIDE, max(1, round(img.height * _SIDE / img.width)))
    else:
        size = (max(1, round(img.width * _SIDE / img.height)), _SIDE)
    return img.resize(size)


def _label(canvas: Image.Image, spot: tuple[int, int], text: str) -> None:
    """Draw a large, high-contrast label in a photo's top-left corner."""
    draw = ImageDraw.Draw(canvas)
    x, y = spot
    draw.rectangle((x, y, x + 56, y + 56), fill=(0, 0, 0))
    font = ImageFont.load_default(size=44)
    draw.text((x + 16, y + 4), text, fill=(255, 255, 255), font=font)
