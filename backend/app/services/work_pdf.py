"""The work-hours report (PDF): totals, periods, weekly chart, tables."""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

from app.services.pdf_blocks import table
from app.services.pdf_text import heading, line
from app.services.work_math import MAX_WEEK_HOURS

_CHART_WEEKS = 52
_BLUE, _GREEN, _RED = (37, 99, 235), (22, 163, 74), (220, 38, 38)


def work_pdf(stats: dict[str, Any]) -> bytes:
    """Build the report from :func:`work_stats.stats`."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    line(pdf, 10, "Phoenix Health Hub - Heures travaillées")
    pdf.set_font("Helvetica", size=10)
    line(pdf, 6, f"Période : {stats['start']} -> {stats['end']}")
    line(pdf, 6, f"Contrat : {stats['contract_hours']:g} h par semaine")
    line(pdf, 6, f"Généré le : {date.today().isoformat()}")
    _summary(pdf, stats)
    _chart(pdf, stats["weeks"][-_CHART_WEEKS:], stats["contract_hours"])
    for title, head, body in _tables(stats):
        table(pdf, title, head, body)
    return bytes(pdf.output())


def _tables(stats: dict[str, Any]) -> list[tuple[str, list[str], list[Any]]]:
    """Periods, weeks and months as (title, header, rows)."""
    periods = [
        [p["label"], p["total_hours"], p["days_worked"], p["week_average"],
         p["overtime_hours"]]
        for p in stats["periods"]
    ]  # fmt: skip
    weeks = [
        [w["week"], w["hours"], w["days"], w["overtime"],
         "oui" if w["over_48h"] else ""]
        for w in stats["weeks"]
    ]  # fmt: skip
    months = [
        [m["month"], m["hours"], m["days"], m["overtime"]]
        for m in stats["months"]
    ]
    return [
        ("Court, moyen et long terme",
         ["Période", "Heures", "Jours", "Moy./semaine", "Heures sup"], periods),
        ("Semaines", ["Semaine", "Heures", "Jours", "Heures sup", "> 48 h"],
         weeks),
        ("Mois", ["Mois", "Heures", "Jours", "Heures sup"], months),
    ]  # fmt: skip


def _summary(pdf: FPDF, stats: dict[str, Any]) -> None:
    """The headline numbers and the legal landmarks."""
    heading(pdf, "Synthèse")
    longest = stats["longest_day"]
    for text in (
        f"Heures travaillées : {stats['total_hours']:g} h sur "
        f"{stats['days_worked']} jours",
        f"Moyenne : {_n(stats['avg_day_hours'])} h par jour travaillé, "
        f"{_n(stats['avg_week_hours'])} h par semaine travaillée",
        f"Embauche moyenne : {stats['avg_start'] or '-'} ; "
        f"débauche moyenne : {stats['avg_end'] or '-'}",
        f"Heures supplémentaires (au-delà du contrat, par semaine) : "
        f"{stats['overtime_hours']:g} h",
        f"Jours de plus de 10 h : {stats['days_over_10h']} ; semaines de "
        f"plus de 48 h : {stats['weeks_over_48h']}",
        "Journée la plus longue : "
        + (f"{longest['date']} ({longest['hours']:g} h)" if longest else "-"),
        "Repères du Code du travail : 10 h par jour et 48 h par semaine au "
        "plus (44 h en moyenne sur 12 semaines).",
    ):
        line(pdf, 6, text)


def _chart(pdf: FPDF, weeks: list[dict[str, Any]], contract: float) -> None:
    """Weekly hours as bars, with the contract and 48 h lines."""
    if not weeks:
        return
    heading(pdf, "Heures par semaine")
    box = (pdf.l_margin, pdf.get_y() + 2, pdf.epw, 50.0)
    top = max([MAX_WEEK_HOURS + 4] + [week["hours"] for week in weeks])
    _bars(pdf, box, top, [week["hours"] for week in weeks])
    x, y, w, h = box
    for level, color in ((contract, _GREEN), (MAX_WEEK_HOURS, _RED)):
        pdf.set_draw_color(*color)
        pdf.line(x, y + h - level / top * h, x + w, y + h - level / top * h)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_y(y + h + 2)
    pdf.set_font("Helvetica", size=8)
    line(pdf, 4, f"Vert : contrat ({contract:g} h). Rouge : 48 h.")
    pdf.set_font("Helvetica", size=10)


def _bars(
    pdf: FPDF,
    box: tuple[float, float, float, float],
    top: float,
    values: list[float],
) -> None:
    """One bar per week, red above 48 h."""
    x, y, w, h = box
    step = w / len(values)
    for index, value in enumerate(values):
        pdf.set_fill_color(*(_RED if value > MAX_WEEK_HOURS else _BLUE))
        height = value / top * h
        left = x + index * step + 0.3
        pdf.rect(left, y + h - height, max(step - 0.6, 0.4), height, "F")


def _n(value: float | None) -> str:
    """A number or a dash."""
    return "-" if value is None else f"{value:g}"
