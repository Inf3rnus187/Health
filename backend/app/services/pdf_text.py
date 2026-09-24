"""Text helpers for the core-font (latin-1) PDF reports."""

from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

#: Common characters outside latin-1 and their closest spelling.
_PLAIN = str.maketrans(
    {
        "œ": "oe",
        "Œ": "OE",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        "…": "...",
        "≥": ">=",
        "≤": "<=",
        "→": "->",
        "›": ">",
        "·": "-",
        " ": " ",
    }
)


def latin(text: str) -> str:
    """Text the core font can print (unknown characters become '?')."""
    return text.translate(_PLAIN).encode("latin-1", "replace").decode("latin-1")


def line(pdf: FPDF, height: float, text: str) -> None:
    """Write one full-width (wrapping) line at the left margin."""
    pdf.multi_cell(
        pdf.epw, height, latin(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )


def heading(pdf: FPDF, text: str, size: int = 12) -> None:
    """A bold section title, then back to body text."""
    pdf.set_font("Helvetica", "B", size)
    line(pdf, 9, text)
    pdf.set_font("Helvetica", size=10)
