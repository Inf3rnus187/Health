"""Render a readable, versioned clinical PDF report (§11).

Groups metrics by domain and, per metric, shows the latest value plus
average / min / max / count over the period — using human labels and
units, not raw metric keys. Text stays latin-1 (core PDF font).
"""

from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.models.report import Report

#: Domain code -> section title (latin-1 safe: no oe ligature).
_DOMAINS = {
    "body": "Corps",
    "heart": "Coeur",
    "rest": "Repos",
    "sleep": "Sommeil",
    "activity": "Activite",
    "fitness": "Forme",
    "vitals": "Signes vitaux",
    "nutrition": "Nutrition",
    "workout": "Seances",
    "apple": "Autres (Apple)",
}


class _Stat(NamedTuple):
    """Aggregates for one metric over the period."""

    n: int
    avg: float
    lo: float
    hi: float
    last: float


def clinical_pdf(
    report: Report, rows: list[dict[str, Any]], meta: dict[str, Any]
) -> bytes:
    """Build a clinical summary PDF grouped by domain."""
    pdf = FPDF()
    pdf.add_page()
    _header(pdf, report)
    groups = _group(rows, meta)
    if not groups:
        pdf.set_font("Helvetica", size=10)
        _line(pdf, 8, "Aucune donnee numerique sur la periode.")
    for domain in sorted(groups):
        _domain(pdf, domain, groups[domain])
    return bytes(pdf.output())


def _line(pdf: FPDF, height: float, text: str) -> None:
    """Write one full-width line (latin-1 safe) at the left margin."""
    safe = text.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(pdf.epw, height, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _header(pdf: FPDF, report: Report) -> None:
    """Write the report title, period and generation date."""
    pdf.set_font("Helvetica", "B", 16)
    _line(pdf, 10, "Phoenix Health Hub - Rapport clinique")
    pdf.set_font("Helvetica", size=10)
    start = report.period_start or "-"
    end = report.period_end or "-"
    _line(pdf, 7, f"Periode: {start} -> {end}")
    _line(pdf, 7, f"Genere le: {date.today().isoformat()}")
    pdf.ln(2)


def _domain(
    pdf: FPDF, domain: str, items: list[tuple[str, str | None, _Stat]]
) -> None:
    """Write one domain section with a line per metric."""
    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 9, _DOMAINS.get(domain, domain.capitalize()))
    pdf.set_font("Helvetica", size=10)
    for label, unit, stat in items:
        _line(pdf, 6, _metric_line(label, unit, stat))
    pdf.ln(1)


def _metric_line(label: str, unit: str | None, stat: _Stat) -> str:
    """One metric's summary line."""
    suffix = f" {unit}" if unit else ""
    return (
        f"{label} : {_num(stat.last)}{suffix}  "
        f"(moy {_num(stat.avg)}, min {_num(stat.lo)}, "
        f"max {_num(stat.hi)}, n={stat.n})"
    )


def _group(
    rows: list[dict[str, Any]], meta: dict[str, Any]
) -> dict[str, list[tuple[str, str | None, _Stat]]]:
    """Bucket per-metric stats by domain, sorted by label."""
    groups: dict[str, list[tuple[str, str | None, _Stat]]] = {}
    for key, stat in _stats(rows).items():
        info = meta.get(key, {})
        domain = info.get("domain", "apple")
        entry = (info.get("label", key), info.get("unit"), stat)
        groups.setdefault(domain, []).append(entry)
    for items in groups.values():
        items.sort(key=lambda entry: entry[0])
    return groups


def _stats(rows: list[dict[str, Any]]) -> dict[str, _Stat]:
    """Compute per-metric aggregates from numeric rows (date-ordered)."""
    values: dict[str, list[float]] = {}
    for row in rows:
        value = row.get("value")
        if isinstance(value, int | float) and not isinstance(value, bool):
            values.setdefault(row["metric_key"], []).append(float(value))
    return {key: _stat(vals) for key, vals in values.items()}


def _stat(values: list[float]) -> _Stat:
    """Build a stat tuple from a metric's numeric values."""
    return _Stat(
        n=len(values),
        avg=sum(values) / len(values),
        lo=min(values),
        hi=max(values),
        last=values[-1],
    )


def _num(value: float) -> str:
    """Format a number: integer when whole, else one decimal."""
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"
