"""Deterministic quality control of a normalized photo (no AI involved).

A photo that is too dark, over-exposed, blurry or tiny cannot be rated
reliably, so it is kept (viewable) but excluded from the scores and the
long-term statistics instead of silently polluting the trend.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageFilter, ImageStat

_MIN_SIDE = 300
_DARK = 35.0
_BRIGHT = 235.0
_BLURRY = 12.0
# Laplacian (edge) filter; the offset keeps negative responses in 0-255.
_LAPLACIAN = ImageFilter.Kernel(
    (3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128
)


def assess(data: bytes) -> dict[str, Any]:
    """Measure brightness, sharpness and size; list blocking issues."""
    with Image.open(io.BytesIO(data)) as img:
        gray = img.convert("L")
        width, height = gray.size
        brightness = float(ImageStat.Stat(gray).mean[0])
        # PIL leaves the 1-px border unfiltered (raw pixels, not edge
        # responses): crop it or it inflates the sharpness of any image.
        edges = gray.filter(_LAPLACIAN).crop((1, 1, width - 1, height - 1))
        sharpness = float(ImageStat.Stat(edges).var[0])
    issues = _issues(min(width, height), brightness, sharpness)
    return {
        "ok": not issues,
        "brightness": round(brightness, 1),
        "sharpness": round(sharpness, 1),
        "width": width,
        "height": height,
        "issues": issues,
    }


def _issues(side: int, brightness: float, sharpness: float) -> list[str]:
    """Return the French labels of the quality problems found."""
    found: list[str] = []
    if side < _MIN_SIDE:
        found.append("Résolution trop faible")
    if brightness < _DARK:
        found.append("Photo trop sombre")
    if brightness > _BRIGHT:
        found.append("Photo surexposée")
    if sharpness < _BLURRY:
        found.append("Photo floue ou vide")
    return found
