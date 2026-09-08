"""Image normalization and EXIF sanitization (§8.3, §12.1).

Works on bytes (not paths) so it composes with optional at-rest
encryption: strips EXIF, auto-orients, bounds the size, re-encodes JPEG.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps

_MAX_SIDE = 1280


def normalize_bytes(data: bytes) -> bytes:
    """Return a clean, oriented, size-bounded JPEG for ``data``."""
    with Image.open(io.BytesIO(data)) as img:
        oriented = ImageOps.exif_transpose(img) or img
        oriented.thumbnail((_MAX_SIDE, _MAX_SIDE))
        out = io.BytesIO()
        oriented.convert("RGB").save(out, format="JPEG", quality=88)
        return out.getvalue()
