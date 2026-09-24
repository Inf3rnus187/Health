"""A PDF whose every page says which report it is.

The footer of each page: the hub, the report's id, when it was made
(local time and zone), the version running, « page n / N » — a page
taken out of a report still says where it comes from.
"""

from __future__ import annotations

from fpdf import FPDF

from app.services.pdf_text import latin


class StampedPDF(FPDF):
    """An A4 PDF with the report's stamp in every footer."""

    def __init__(self, stamp: str) -> None:
        """``stamp``: the footer line (id, time, version)."""
        super().__init__()
        self.stamp = stamp

    def footer(self) -> None:
        """The stamp and the page number, small and grey."""
        self.set_y(-12)
        self.set_font("Helvetica", size=7)
        self.set_text_color(110, 110, 110)
        text = f"{self.stamp} - page {self.page_no()}/{{nb}}"
        self.cell(0, 5, latin(text), align="C")
        self.set_text_color(0, 0, 0)
