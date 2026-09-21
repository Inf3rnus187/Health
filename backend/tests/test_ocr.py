"""OCR fallback for scanned PDFs: graceful degradation + a live roundtrip."""

from __future__ import annotations

import pymupdf
import pytest
from app.services import biology, ocr


def test_available_returns_bool() -> None:
    assert isinstance(ocr.available(), bool)


def test_ocr_pdf_rejects_non_pdf() -> None:
    assert ocr.ocr_pdf(b"this is not a pdf") == ""


def _scanned_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    for index, line in enumerate(text.splitlines()):
        page.insert_text((60, 80 + index * 26), line, fontsize=15)
    pix = page.get_pixmap(dpi=200)
    scan = pymupdf.open()
    image_page = scan.new_page(width=pix.width, height=pix.height)
    image_page.insert_image(image_page.rect, stream=pix.tobytes("png"))
    return scan.tobytes()


@pytest.mark.skipif(not ocr.available(), reason="tesseract not installed")
def test_ocr_reads_a_scanned_page() -> None:
    text = ocr.ocr_pdf(_scanned_pdf("Hemoglobine 15,9 g/dL"))
    assert "emoglob" in text or "15" in text


@pytest.mark.skipif(not ocr.available(), reason="tesseract not installed")
def test_biology_parses_a_scanned_lab() -> None:
    scan = _scanned_pdf(
        "Preleve le 11-09-2026 12:02\n"
        "Hemoglobine 15,9 g/dL (13,4-16,7)\n"
        "Glycemie a jeun 1,61 g/L (0,70-1,10)"
    )
    keys = {r.key for r in biology.parse_text(biology._extract(scan))}
    assert "bio.hemoglobine" in keys
