"""Text (and page images) of any uploaded medical document.

A PDF with a text layer is read directly; a scanned PDF or a photo of a
document is OCR'd (the OCR text is what every AI-proposed value is
checked against) and its pages are kept as images for a vision model.
"""

from __future__ import annotations

from io import BytesIO
from typing import NamedTuple

from pypdf import PdfReader

from app.services import imaging, ocr

_MIN_TEXT = 40  # fewer characters than this = no usable text layer


class DocContent(NamedTuple):
    """What a model may read from a document."""

    text: str
    images: list[bytes]
    scanned: bool


def extract(data: bytes, media_type: str) -> DocContent:
    """Text and, for scanned documents, page images."""
    if media_type == "application/pdf" or data[:5] == b"%PDF-":
        return _pdf(data)
    if media_type.startswith("image/"):
        return DocContent(ocr.ocr_image(data), [_jpeg(data)], scanned=True)
    if media_type.startswith("text/"):
        return DocContent(data.decode("utf-8", "replace"), [], scanned=False)
    return DocContent("", [], scanned=False)


def _pdf(data: bytes) -> DocContent:
    """A PDF's text layer, else its OCR text plus page images."""
    try:
        reader = PdfReader(BytesIO(data))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception:  # noqa: BLE001 - a broken PDF is just unreadable
        text = ""
    if len(text.strip()) >= _MIN_TEXT:
        return DocContent(text, [], scanned=False)
    return DocContent(ocr.ocr_pdf(data), ocr.pdf_pages(data), scanned=True)


def _jpeg(data: bytes) -> bytes:
    """A photographed document as a bounded, oriented JPEG."""
    try:
        return imaging.normalize_bytes(data)
    except Exception:  # noqa: BLE001 - keep the original bytes
        return data
