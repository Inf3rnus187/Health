"""Small PDF building blocks shared by the reports: ruled tables."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

from app.services.pdf_text import heading, latin


def table(
    pdf: FPDF,
    title: str,
    head: list[str],
    body: list[list[Any]],
    widths: list[float] | None = None,
) -> None:
    """A ruled table under a heading (nothing when ``body`` is empty).

    ``widths`` are fractions of the page width (equal columns if None).
    """
    if not body:
        return
    heading(pdf, title)
    shares = widths or [1 / len(head)] * len(head)
    sizes = [pdf.epw * share for share in shares]
    pdf.set_font("Helvetica", "B", 8)
    for size, cell in zip(sizes, head, strict=True):
        pdf.cell(size, 6, latin(cell), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", size=8)
    for row in body:
        for size, cell in zip(sizes, row, strict=True):
            pdf.cell(size, 5, latin(cell_text(cell)), border=1)
        pdf.ln()
    pdf.set_font("Helvetica", size=10)
    pdf.set_x(pdf.l_margin)


def cell_text(value: Any) -> str:
    """A table cell: numbers without trailing zeros, None as a dash."""
    if value is None:
        return "-"
    return f"{value:g}" if isinstance(value, float) else str(value)
