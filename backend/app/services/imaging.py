"""Image normalization and EXIF sanitization (§8.3, §12.1).

Works on bytes (not paths) so it composes with optional at-rest
encryption: strips EXIF, auto-orients, bounds the size, re-encodes JPEG.
"""

from __future__ import annotations

import io

import pillow_heif
from PIL import Image, ImageOps

# Apple devices (and mirror cameras) capture HEIC/HEIF, which PIL and web
# browsers cannot read natively; registering the opener lets us decode it
# and re-encode a browser-safe JPEG.
pillow_heif.register_heif_opener()

_MAX_SIDE = 1280


def normalize_bytes(data: bytes) -> bytes:
    """Return a clean, oriented, size-bounded JPEG for ``data``."""
    with Image.open(io.BytesIO(data)) as img:
        oriented = ImageOps.exif_transpose(img) or img
        oriented.thumbnail((_MAX_SIDE, _MAX_SIDE))
        out = io.BytesIO()
        oriented.convert("RGB").save(out, format="JPEG", quality=88)
        return out.getvalue()
