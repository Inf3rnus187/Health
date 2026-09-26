"""Render a readable clinical PDF a doctor can act on (§11).

Three parts: a "Faits marquants" recap, trend line-charts of the key
indicators (drawn as vectors — no chart dependency), and per-domain tables
with latest / average / min / max / count. Human labels + units, not raw
metric keys. All text is latin-1 (core PDF font).
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, NamedTuple

from fpdf import FPDF

from app.models.report import Report
from app.services import (
    domain_labels,
    pdf_blocks,
    pdf_stamp,
    reports_pdf_ai,
    reports_pdf_evidence,
)
from app.services.pdf_text import latin as _latin
from app.services.pdf_text import line as _line

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
#: Where a value came from, as a reader says it.
_SOURCE_FR = {
    "apple_health": "Apple Santé",
    "auto-export": "Health Auto Export",
    "healthkit": "app iPhone (HealthKit)",
    "watch": "montre et compteurs",
    "manual": "saisie",
    "meal": "repas analysés",
    "import": "import de fichiers",
    "ppc": "PPC",
}
_AUTHENTIC = (
    "Authenticité : l'empreinte SHA-256 de ce fichier est enregistrée par "
    "le hub à sa création ; Rapports › « Vérifier un fichier » dit si une "
    "copie est identique."
)


class _Stat(NamedTuple):
    """Aggregates for one metric over the period."""

    n: int
    avg: float
    lo: float
    hi: float
    last: float


def clinical_pdf(
    report: Report,
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    care: dict[str, list[str]] | None = None,
    synthesis: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> bytes:
    """Build a caregiver summary: recap, facts, care record, charts, tables.

    With ``synthesis`` (the AI clinical synthesis) it comes first and its
    numbered facts are appended at the end. ``extra``: ``facts`` (habits,
    adherence, meals, traceability of the period) and ``stamp``
    (generated, version, data_sha256) printed in the header and on every
    page.
    """
    extra = extra or {}
    stamp = extra.get("stamp") or {}
    pdf = pdf_stamp.StampedPDF(_stamp_line(report, stamp))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, report, stamp, rows)
    reports_pdf_ai.synthesis(pdf, synthesis)
    series = _series(rows)
    _recap(pdf, series, meta)
    reports_pdf_evidence.sections(pdf, extra.get("facts"))
    _care_sections(pdf, care)
    _charts(pdf, series, meta)
    _tables(pdf, series, meta)
    _yes_no(pdf, rows, meta)
    reports_pdf_evidence.trace(pdf, extra.get("facts"))
    reports_pdf_ai.facts(pdf, synthesis)
    return bytes(pdf.output())


def _care_sections(pdf: FPDF, care: dict[str, list[str]] | None) -> None:
    """Write the care record: conditions, treatments, appointments, docs."""
    if not care:
        return
    for title, lines in care.items():
        if not lines:
            continue
        pdf.set_font("Helvetica", "B", 12)
        _line(pdf, 9, title)
        pdf.set_font("Helvetica", size=10)
        for text in lines:
            _line(pdf, 6, text)
        pdf.ln(1)


def _header(
    pdf: FPDF, report: Report, stamp: dict[str, Any], rows: list[dict[str, Any]]
) -> None:
    """Title, period, the report's identity, sources and fingerprint."""
    pdf.set_font("Helvetica", "B", 16)
    _line(pdf, 10, "Phoenix Health Hub - Rapport clinique")
    pdf.set_font("Helvetica", size=9)
    start = report.period_start or "-"
    end = report.period_end or "-"
    _line(pdf, 5, f"Période : {start} -> {end}")
    _line(pdf, 5, f"Rapport n° {report.id}")
    made = stamp.get("generated") or date.today().isoformat()
    _line(pdf, 5, f"Généré le {made} - version {stamp.get('version') or '-'}")
    _line(pdf, 5, f"Sources des valeurs : {_sources(rows)}")
    if stamp.get("data_sha256"):
        _line(
            pdf, 5, f"Empreinte des données (SHA-256) : {stamp['data_sha256']}"
        )
    _line(pdf, 5, _AUTHENTIC)
    pdf.set_font("Helvetica", size=10)
    pdf.ln(2)


def _stamp_line(report: Report, stamp: dict[str, Any]) -> str:
    """The footer of every page."""
    made = stamp.get("generated") or date.today().isoformat()
    return f"Phoenix Health Hub - rapport {report.id} - {made}"


def _sources(rows: list[dict[str, Any]]) -> str:
    """How many values came from each source (« Apple Santé 3 400 »)."""
    count = Counter(str(r.get("source") or "?") for r in rows)
    if not count:
        return "aucune valeur"
    return ", ".join(
        f"{_SOURCE_FR.get(k, k)} {n}" for k, n in count.most_common()
    )


def _yes_no(
    pdf: FPDF, rows: list[dict[str, Any]], meta: dict[str, Any]
) -> None:
    """Yes / no answers (a medicine taken…): yes, no, days recorded."""
    answers: dict[str, list[bool]] = {}
    for row in rows:
        if isinstance(row.get("value"), bool):
            answers.setdefault(row["metric_key"], []).append(row["value"])
    body = [
        [meta.get(k, {}).get("label", k), sum(v), len(v) - sum(v), len(v)]
        for k, v in sorted(answers.items())
    ]
    head = ["Question", "Oui (jours)", "Non (jours)", "Jours saisis"]
    pdf_blocks.table(pdf, "Réponses oui / non", head, body)


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
    _line(pdf, 9, domain_labels.label(domain))
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
