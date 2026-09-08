"""Render a simple, versioned clinical PDF report (§11)."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.models.report import Report


def clinical_pdf(report: Report, rows: list[dict[str, Any]]) -> bytes:
    """Build a one-page clinical summary PDF from tidy rows."""
    pdf = FPDF()
    pdf.add_page()
    _header(pdf, report)
    _summary(pdf, rows)
    return bytes(pdf.output())


def _line(pdf: FPDF, height: float, text: str) -> None:
    """Write one full-width line and return to the left margin."""
    pdf.multi_cell(pdf.epw, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _header(pdf: FPDF, report: Report) -> None:
    """Write the report title and period."""
    pdf.set_font("Helvetica", "B", 16)
    _line(pdf, 10, "Phoenix Health Hub - Rapport clinique")
    pdf.set_font("Helvetica", size=10)
    start = report.period_start or "-"
    end = report.period_end or "-"
    _line(pdf, 8, f"Periode: {start} -> {end}")
    pdf.ln(2)


def _summary(pdf: FPDF, rows: list[dict[str, Any]]) -> None:
    """Write per-metric averages."""
    averages = _averages(rows)
    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 10, "Moyennes par metrique")
    pdf.set_font("Helvetica", size=10)
    for key, value in sorted(averages.items()):
        _line(pdf, 7, f"{key}: {value:.2f}")


def _averages(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Average numeric values per metric key."""
    totals: dict[str, list[float]] = {}
    for row in rows:
        value = row.get("value")
        if isinstance(value, int | float) and not isinstance(value, bool):
            totals.setdefault(row["metric_key"], []).append(float(value))
    return {key: sum(vals) / len(vals) for key, vals in totals.items()}
