"""The work-hours report (PDF): totals, periods, weekly chart, tables."""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

from app.services import work_absence
from app.services.pdf_blocks import table
from app.services.pdf_text import heading, line
from app.services.work_math import MAX_WEEK_HOURS

_CHART_WEEKS = 52
_BLUE, _GREEN, _RED = (37, 99, 235), (22, 163, 74), (220, 38, 38)
_ORANGE = (245, 158, 11)
_PURPLE = (139, 92, 246)


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
        [p["label"], p["total_hours"], p["days_worked"], p["absent_days"],
         p["week_average"] if p["week_average"] is not None else "-",
         p["overtime_hours"]]
        for p in stats["periods"]
    ]  # fmt: skip
    weeks = [
        [w["week"], w["hours"], w["remote"] or "", w["days"], w["overtime"],
         "oui" if w["over_48h"] else "", w["absent_days"] or "",
         w["target"]]
        for w in stats["weeks"]
    ]  # fmt: skip
    months = [
        [m["month"], m["hours"], m["remote"] or "", m["days"], m["overtime"]]
        for m in stats["months"]
    ]
    return [
        ("Court, moyen et long terme",
         ["Période", "Heures", "Jours", "Absent (j)", "Moy./sem. présente",
          "Heures sup"], periods),
        ("Semaines", ["Semaine", "Heures", "Distance", "Jours", "Heures sup",
                      "> 48 h", "Absent (j)", "Objectif"], weeks),
        ("Mois", ["Mois", "Heures", "Distance", "Jours", "Heures sup"],
         months),
    ]  # fmt: skip


def _summary(pdf: FPDF, stats: dict[str, Any]) -> None:
    """The headline numbers and the legal landmarks."""
    heading(pdf, "Synthèse")
    longest = stats["longest_day"]
    for text in (
        f"Heures travaillées : {stats['total_hours']:g} h sur "
        f"{stats['days_worked']} jours",
        f"Moyenne : {_n(stats['avg_day_hours'])} h par jour travaillé, "
        f"{_n(stats['avg_week_hours'])} h par semaine"
        " complète (sans absence ni férié)",
        f"Embauche moyenne : {stats['avg_start'] or '-'} ; "
        f"débauche moyenne : {stats['avg_end'] or '-'}",
        f"Heures supplémentaires (au-delà du contrat, par semaine) : "
        f"{stats['overtime_hours']:g} h",
        f"Jours de plus de 10 h : {stats['days_over_10h']} ; semaines de "
        f"plus de 48 h : {stats['weeks_over_48h']}",
        "Journée la plus longue : "
        + (f"{longest['date']} ({longest['hours']:g} h)" if longest else "-"),
        *work_absence.texts(stats),
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
    _bars(pdf, box, top, weeks)
    x, y, w, h = box
    for level, color in ((contract, _GREEN), (MAX_WEEK_HOURS, _RED)):
        pdf.set_draw_color(*color)
        pdf.line(x, y + h - level / top * h, x + w, y + h - level / top * h)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_y(y + h + 2)
    pdf.set_font("Helvetica", size=8)
    line(
        pdf,
        4,
        f"Vert : contrat ({contract:g} h). Rouge : 48 h. Barre orange : "
        "semaine avec absence ou jour férié (trait vert : objectif réduit). "
        "Violet : heures à distance.",
    )
    pdf.set_font("Helvetica", size=10)


def _bars(
    pdf: FPDF,
    box: tuple[float, float, float, float],
    top: float,
    weeks: list[dict[str, Any]],
) -> None:
    """One bar per week: red above 48 h, else orange with days off."""
    x, y, w, h = box
    step = w / len(weeks)
    for index, week in enumerate(weeks):
        value = week["hours"]
        color = _ORANGE if week.get("absent_days") else _BLUE
        pdf.set_fill_color(*(_RED if value > MAX_WEEK_HOURS else color))
        height = value / top * h
        left = x + index * step + 0.3
        width = max(step - 0.6, 0.4)
        pdf.rect(left, y + h - height, width, height, "F")
        if week.get("remote"):  # the part worked remote, on top
            pdf.set_fill_color(*_PURPLE)
            pdf.rect(left, y + h - height, width, week["remote"] / top * h, "F")
        if week.get("absent_days"):  # the week's reduced target
            level = y + h - week["target"] / top * h
            pdf.set_draw_color(*_GREEN)
            pdf.line(left, level, left + width, level)
            pdf.set_draw_color(0, 0, 0)


def _n(value: float | None) -> str:
    """A number or a dash."""
    return "-" if value is None else f"{value:g}"
