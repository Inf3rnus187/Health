"""Image normalization and EXIF sanitization (§8.3, §12.1).

Re-encodes uploads without EXIF (stripping location/device metadata),
auto-orients them, and bounds the size for consistent framing.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

_MAX_SIDE = 1280


def normalize(source: Path, target: Path) -> None:
    """Write a clean, oriented, size-bounded JPEG to ``target``."""
    with Image.open(source) as img:
        oriented = ImageOps.exif_transpose(img) or img
        oriented.thumbnail((_MAX_SIDE, _MAX_SIDE))
        target.parent.mkdir(parents=True, exist_ok=True)
        oriented.convert("RGB").save(target, format="JPEG", quality=88)
