"""Read a product's barcode on a photo, on the hub, offline.

EAN-13, EAN-8, UPC-A and UPC-E (the codes printed on food packs) are
decoded by zxing-cpp from a photo — taken with the camera or picked
from the gallery, HEIC included — even tilted or upside down; nothing is
sent anywhere. Returns the codes found (digits), best first.
"""

from __future__ import annotations

import io

import zxingcpp
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.errors import InvalidInputError
from app.services import imaging  # noqa: F401 - registers the HEIC opener

_FORMATS = zxingcpp.barcode_formats_from_str("EAN13,EAN8,UPCA,UPCE")
_SIDE = 2400
_DIGITS = range(8, 15)


def read(data: bytes) -> list[str]:
    """The product barcodes on the photo ([] when none is readable)."""
    if not data:
        raise InvalidInputError("Empty photo")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise InvalidInputError("Image exceeds the size limit")
    try:
        with Image.open(io.BytesIO(data)) as img:
            oriented = ImageOps.exif_transpose(img) or img
            oriented.thumbnail((_SIDE, _SIDE))
            gray = oriented.convert("L")
    except Exception as exc:  # noqa: BLE001 - any decoding failure
        raise InvalidInputError("Unreadable image") from exc
    codes: list[str] = []
    for found in zxingcpp.read_barcodes(gray, formats=_FORMATS):
        text = found.text.strip()
        if text.isdigit() and len(text) in _DIGITS and text not in codes:
            codes.append(text)
    return codes
