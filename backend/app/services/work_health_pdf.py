"""The work ↔ health report (PDF), built from :func:`work_health.gather`.

Facts first, sources stated, nothing estimated without saying so: the
method, the work summary and the legal landmarks here; sleep, periods,
absences, the day-by-day journal and the evidence annex in
:mod:`work_health_pdf_more`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

from app.services import work_health_pdf_more as more
from app.services.pdf_blocks import table
from app.services.pdf_text import heading, line

_DAY = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")


def build(data: dict[str, Any], images: dict[str, bytes]) -> bytes:
    """The whole report; ``images`` maps evidence ids to image bytes."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _header(pdf, data)
    _method(pdf, data)
    _work(pdf, data)
    _legal(pdf, data)
    more.sleep(pdf, data)
    more.periods(pdf, data)
    more.absences(pdf, data)
    more.journal(pdf, data)
    more.evidence(pdf, data, images)
    return bytes(pdf.output())


def _header(pdf: FPDF, data: dict[str, Any]) -> None:
    """Title, period, contract, date."""
    pdf.set_font("Helvetica", "B", 16)
    line(pdf, 10, "Dossier travail et santé")
    pdf.set_font("Helvetica", size=10)
    line(pdf, 6, f"Période : {_d(data['start'])} au {_d(data['end'])}")
    line(pdf, 6, f"Contrat : {data['contract_hours']:g} h par semaine")
    line(pdf, 6, f"Généré le {_d(date.today())} par Phoenix Health Hub.")
    line(
        pdf,
        6,
        "Ce document rassemble des faits enregistrés ; il n'est ni un avis "
        "médical ni un avis juridique.",
    )


def _method(pdf: FPDF, data: dict[str, Any]) -> None:
    """Where every number comes from, and what is missing."""
    src = data["sources"]
    names = {
        "tap": "pointage (Raccourci / GPS)",
        "import": "historique importé",
        "manual": "saisie",
        "edited": "complétée à la main",
    }
    by = ", ".join(
        f"{n} {names.get(k, k)}" for k, n in src["by_source"].items()
    )
    heading(pdf, "Méthode et sources")
    for text in (
        f"Sessions de travail : {src['sessions']} ({by or 'aucune'}).",
        f"Journées incomplètes : {src['missing_start']} débauches sans "
        f"embauche pointée, {src['missing_end']} embauches sans débauche. "
        "Leurs heures ne sont pas comptées : les totaux sont des minimums.",
        f"Nuits de sommeil connues : {src['nights']} "
        f"({_counts(src['nights_by_source'])}) ; jours travaillés sans "
        f"donnée de sommeil : {src['worked_days_without_night']}.",
        "Une nuit est rattachée au jour du réveil ; le sommeil « après » "
        "un jour de travail est celui de la nuit suivante.",
        "Chaque preuve jointe est identifiée par son empreinte SHA-256, "
        "calculée à sa réception.",
    ):
        line(pdf, 5, text)


def _work(pdf: FPDF, data: dict[str, Any]) -> None:
    """The headline work numbers."""
    w = data["work"]
    longest = w["longest_day"]
    heading(pdf, "Travail : synthèse")
    for text in (
        f"Heures travaillées (sessions complètes) : {w['total_hours']:g} h "
        f"sur {w['days_worked']} jours.",
        f"Jours de présence pointée (au moins une embauche ou une "
        f"débauche) : {sum(1 for r in data['days'] if r['worked'])}.",
        f"Moyenne : {_n(w['avg_day_hours'])} h par jour travaillé, "
        f"{_n(w['avg_week_hours'])} h par semaine travaillée.",
        f"Embauche moyenne {w['avg_start'] or '-'}, débauche moyenne "
        f"{w['avg_end'] or '-'}.",
        f"Heures au-delà du contrat (par semaine) : {w['overtime_hours']:g} h.",
        f"Jours de plus de 10 h : {w['days_over_10h']} ; semaines de plus "
        f"de 48 h : {w['weeks_over_48h']}.",
        "Journée la plus longue : "
        + (
            f"{_d(longest['date'])}, {longest['hours']:g} h" if longest else "-"
        ),
    ):
        line(pdf, 5, text)


def _legal(pdf: FPDF, data: dict[str, Any]) -> None:
    """Code du travail landmarks and the days concerned."""
    lg = data["legal"]
    heading(pdf, "Repères du Code du travail")
    line(
        pdf,
        5,
        f"Heures de nuit (21 h - 6 h) : {lg['night_hours']:g} h ; plus longue "
        f"suite de jours travaillés : {lg['max_consecutive_days']}.",
    )
    table(
        pdf,
        "Jours concernés",
        ["Repère", "Nombre", "Dates (les 12 premières)"],
        _legal_rows(lg),
        [0.3, 0.1, 0.6],
    )


def _legal_rows(lg: dict[str, Any]) -> list[list[Any]]:
    """One row per landmark: name, count, first dates."""
    windows = ", ".join(
        f"dès {_d(w['from'])} ({w['average']:g} h)"
        for w in lg["over_44h_12_weeks"][:6]
    )
    return [
        ["Repos quotidien < 11 h", len(lg["short_rests"]),
         _list(lg["short_rests"], "rest_hours")],
        ["Amplitude > 13 h", len(lg["spread_over_13h"]),
         _list(lg["spread_over_13h"], "hours")],
        ["Sessions de 12 h et plus", len(lg["long_sessions"]),
         _list(lg["long_sessions"], "hours")],
        ["Moyenne > 44 h sur 12 semaines", len(lg["over_44h_12_weeks"]),
         windows],
        ["Dimanches travaillés", len(lg["sundays"]), _dates(lg["sundays"])],
        ["Jours fériés travaillés", len(lg["holidays"]),
         _dates(lg["holidays"])],
    ]  # fmt: skip


def _list(items: list[dict[str, Any]], key: str) -> str:
    """The first dates of a landmark with their value."""
    return ", ".join(f"{_d(i['date'])} ({i[key]:g} h)" for i in items[:12])


def _dates(days: list[date]) -> str:
    """The first dates of a list."""
    return ", ".join(_d(d) for d in days[:12])


def _counts(counts: dict[str, int]) -> str:
    """``{'apple': 3}`` as ``3 apple``."""
    return ", ".join(f"{n} {k}" for k, n in counts.items()) or "aucune"


def _d(day: date) -> str:
    """A date as ``lun 02/03/2026``."""
    return f"{_DAY[day.weekday()]} {day:%d/%m/%Y}"


def _n(value: float | None) -> str:
    """A number or a dash."""
    return "-" if value is None else f"{value:g}"
