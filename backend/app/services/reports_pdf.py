"""Render a readable clinical PDF a doctor can act on (§11).

Three parts: a "Faits marquants" recap, trend line-charts of the key
indicators (drawn as vectors — no chart dependency), and per-domain tables
with latest / average / min / max / count. Human labels + units, not raw
metric keys. All text is latin-1 (core PDF font).
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

#: Doctor-relevant metrics highlighted in the recap and charted.
_KEY_METRICS = (
    "body.weight",
    "rest.hr",
    "heart.rate",
    "heart.hrv",
    "body.spo2",
    "body.resp_rate",
    "sleep.asleep",
    "activity.steps",
)
_MIN_POINTS = 2


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
    """Build a clinical summary: recap, trend charts, per-domain tables."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, report)
    series = _series(rows)
    _recap(pdf, series, meta)
    _charts(pdf, series, meta)
    _tables(pdf, series, meta)
    return bytes(pdf.output())


def _latin(text: str) -> str:
    """Coerce text to latin-1 (core font can't encode more)."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _line(pdf: FPDF, height: float, text: str) -> None:
    """Write one full-width line at the left margin."""
    pdf.multi_cell(
        pdf.epw, height, _latin(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )


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


def _recap(
    pdf: FPDF, series: dict[str, list[float]], meta: dict[str, Any]
) -> None:
    """Write the quick-glance highlights for the key metrics."""
    lines = []
    for key in _KEY_METRICS:
        values = series.get(key)
        if not values:
            continue
        info = meta.get(key, {})
        unit = info.get("unit") or ""
        lines.append(f"{info.get('label', key)} : {_num(values[-1])} {unit}")
    if not lines:
        return
    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 9, "Faits marquants")
    pdf.set_font("Helvetica", size=10)
    for text in lines:
        _line(pdf, 6, text.strip())
    pdf.ln(2)


def _charts(
    pdf: FPDF, series: dict[str, list[float]], meta: dict[str, Any]
) -> None:
    """Draw a 2-column grid of trend line-charts for the key metrics."""
    keys = [k for k in _KEY_METRICS if len(series.get(k, [])) >= _MIN_POINTS]
    if not keys:
        return
    pdf.set_font("Helvetica", "B", 12)
    _line(pdf, 9, "Evolution des indicateurs cles")
    col_w = (pdf.epw - 8) / 2
    row_y = pdf.get_y()
    for i, key in enumerate(keys):
        col = i % 2
        if col == 0:
            row_y = _row_top(pdf, 36)
        x = pdf.l_margin + col * (col_w + 8)
        _one_chart(pdf, x, row_y, col_w, key, series[key], meta)
    pdf.set_y(row_y + 36)


def _row_top(pdf: FPDF, needed: float) -> float:
    """Start a new page if a chart row would overflow; return its top y."""
    if pdf.get_y() + needed > pdf.h - pdf.b_margin:
        pdf.add_page()
    return pdf.get_y()


def _one_chart(
    pdf: FPDF,
    x: float,
    y: float,
    w: float,
    key: str,
    values: list[float],
    meta: dict[str, Any],
) -> None:
    """Draw one labelled chart: title, sparkline box, last/min/max."""
    info = meta.get(key, {})
    pdf.set_xy(x, y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(w, 5, _latin(info.get("label", key)))
    _chart(pdf, x, y + 6, w, 22, values)
    pdf.set_xy(x, y + 29)
    pdf.set_font("Helvetica", size=7)
    unit = info.get("unit") or ""
    caption = f"min {_num(min(values))} - max {_num(max(values))} {unit}"
    pdf.cell(w, 4, _latin(caption.strip()))


def _chart(
    pdf: FPDF, x: float, y: float, w: float, h: float, values: list[float]
) -> None:
    """Draw the axes box and the value polyline inside it."""
    pdf.set_draw_color(210, 210, 210)
    pdf.set_line_width(0.2)
    pdf.rect(x, y, w, h)
    lo = min(values)
    span = (max(values) - lo) or 1.0
    step = w / (len(values) - 1)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.5)
    pts = [
        (x + i * step, y + h - (v - lo) / span * h)
        for i, v in enumerate(values)
    ]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
        pdf.line(x1, y1, x2, y2)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.2)


def _tables(
    pdf: FPDF, series: dict[str, list[float]], meta: dict[str, Any]
) -> None:
    """Write per-domain tables of latest/avg/min/max/count."""
    groups = _group(series, meta)
    if not groups:
        pdf.set_font("Helvetica", size=10)
        _line(pdf, 8, "Aucune donnee numerique sur la periode.")
    for domain in sorted(groups):
        _domain(pdf, domain, groups[domain])


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
    series: dict[str, list[float]], meta: dict[str, Any]
) -> dict[str, list[tuple[str, str | None, _Stat]]]:
    """Bucket per-metric stats by domain, sorted by label."""
    groups: dict[str, list[tuple[str, str | None, _Stat]]] = {}
    for key, values in series.items():
        info = meta.get(key, {})
        entry = (info.get("label", key), info.get("unit"), _stat(values))
        groups.setdefault(info.get("domain", "apple"), []).append(entry)
    for items in groups.values():
        items.sort(key=lambda entry: entry[0])
    return groups


def _series(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Per-metric numeric values in date order (rows are date-ordered)."""
    out: dict[str, list[float]] = {}
    for row in rows:
        value = row.get("value")
        if isinstance(value, int | float) and not isinstance(value, bool):
            out.setdefault(row["metric_key"], []).append(float(value))
    return out


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
