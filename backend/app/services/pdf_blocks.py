"""Small PDF building blocks shared by the reports: ruled tables."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.services.pdf_text import heading, latin


def table(
    pdf: FPDF,
    title: str,
    head: list[str],
    body: list[list[Any]],
    widths: list[float] | None = None,
) -> None:
    """A ruled table under a heading (nothing when ``body`` is empty).

    ``widths`` are fractions of the page width (equal columns if None);
    a long cell wraps, a row never runs off the page, the heading row is
    repeated on the next page.
    """
    if not body:
        return
    heading(pdf, title)
    shares = widths or [1 / len(head)] * len(head)
    pdf.set_font("Helvetica", size=8)
    pdf.set_fill_color(255, 255, 255)  # a chart before may leave its colour
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    with pdf.table(
        col_widths=tuple(shares),
        width=pdf.epw,
        line_height=4,
        padding=(0.6, 1),
        text_align="LEFT",
        headings_style=FontFace(emphasis="BOLD"),
        cell_fill_mode="NONE",
    ) as grid:
        for values in (head, *body):
            row = grid.row()
            for value in values:
                row.cell(latin(cell_text(value)))
    pdf.set_font("Helvetica", size=10)
    pdf.set_x(pdf.l_margin)


def cell_text(value: Any) -> str:
    """A table cell: numbers without trailing zeros, None as a dash."""
    if value is None:
        return "-"
    return f"{value:g}" if isinstance(value, float) else str(value)
