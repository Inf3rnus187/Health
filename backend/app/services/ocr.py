"""Optional OCR for scanned (image-only) PDFs.

A text PDF is read directly with pypdf; a scanned report has no text
layer, so each page is rasterized (PyMuPDF) and read with Tesseract in
French. Tesseract is a system binary — when it or the imaging libraries
are missing these helpers return an empty string, so callers degrade
gracefully and still keep the uploaded document.
"""

from __future__ import annotations

import io
from typing import Any

_DPI = 200
_MAX_PAGES = 12


def available() -> bool:
    """True when OCR (PyMuPDF + Tesseract) can run in this environment."""
    try:
        import pymupdf  # noqa: F401
        import pytesseract
    except ImportError:
        return False
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return False
    return True


def ocr_pdf(data: bytes, *, lang: str = "fra+eng") -> str:
    """Return OCR text for a scanned PDF, or '' when OCR is unavailable."""
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        doc: Any = pymupdf.open(  # type: ignore[no-untyped-call]
            stream=data, filetype="pdf"
        )
    except Exception:
        return ""
    pages: list[str] = []
    for page in list(doc)[:_MAX_PAGES]:
        png = page.get_pixmap(dpi=_DPI).tobytes("png")
        image = Image.open(io.BytesIO(png))
        pages.append(pytesseract.image_to_string(image, lang=lang))
    doc.close()
    return "\n".join(pages)
