"""The report's factual sections: habits, medication, meals, traceability.

Numbers only, each with what it is computed on (days recorded out of the
period's days): a reader can check every line against the data. A day
without an entry is written « sans donnée », never counted as zero.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

from app.services import pdf_blocks
from app.services.evidence_habits import COUNTERS
from app.services.pdf_text import heading, line

_NO_ZERO = (
    "Un jour sans saisie n'est pas un jour à zéro : il est compté « sans "
    "donnée » (un zéro se confirme avec « 0 » dans le Journal). Moyennes "
    "sur les jours saisis ; barres vides : jours sans donnée."
)
#: Meal type → French.
_MEALS_FR = {
    "breakfast": "petit-déjeuner",
    "lunch": "déjeuner",
    "snack": "collation",
    "dinner": "dîner",
}
_CHART_H = 26


def sections(pdf: FPDF, facts: dict[str, Any] | None) -> None:
    """Habits, medication adherence and meals of the period."""
    if not facts:
        return
    _habits(pdf, facts.get("habits") or [], facts)
    _medications(pdf, facts.get("medications") or [])
    _meals(pdf, facts.get("meals") or {})


_TRACE_NOTE = (
    "Chaque saisie est horodatée par le hub à son arrivée. « Le jour "
    "même » : saisie le jour qu'elle concerne ; « après coup » : un jour "
    "suivant."
)
_TRACE_HEAD = ["Compteur", "Saisies", "Le jour même", "Après coup", "Canaux"]


def trace(pdf: FPDF, facts: dict[str, Any] | None) -> None:
    """When and how the entries were made (the proof of recording)."""
    found = (facts or {}).get("trace") or {}
    if not any(found.values()):
        return
    heading(pdf, "Traçabilité des saisies")
    pdf.set_font("Helvetica", size=9)
    line(pdf, 5, _TRACE_NOTE)
    rows = [_tap_row(c) for c in found.get("counters") or []]
    widths = [0.3, 0.12, 0.16, 0.16, 0.26]
    pdf_blocks.table(pdf, "Compteurs", _TRACE_HEAD, rows, widths)
    _timing(pdf, "Prises de médicaments", found.get("medications") or {})
    _timing(pdf, "Repas", found.get("meals") or {})


def _tap_row(counter: dict[str, Any]) -> list[Any]:
    """One counter's entries as a table row."""
    return [
        COUNTERS.get(counter["metric"], counter["metric"]),
        counter["entries"],
        counter["same_day"],
        counter["later"],
        _channels(counter["channels"]),
    ]


def _habits(
    pdf: FPDF, items: list[dict[str, Any]], facts: dict[str, Any]
) -> None:
    """One line per counter, the cigarettes per day, before / after."""
    if not items:
        return
    heading(pdf, f"Habitudes enregistrées ({facts['start']} -> {facts['end']})")
    pdf.set_font("Helvetica", size=9)
    line(pdf, 5, _NO_ZERO)
    head = [
        "Compteur",
        "Jours saisis",
        "Total",
        "Moy./jour saisi",
        "Médiane",
        "Plus bas",
        "Plus haut",
    ]
    rows = [_habit_row(i) for i in items]
    pdf_blocks.table(
        pdf, "Faits", head, rows, [0.22, 0.13, 0.1, 0.13, 0.1, 0.16, 0.16]
    )
    for item in items:
        if item["key"] == "habit.cigarettes":
            _bars(pdf, item)
            _periods(pdf, item)
    _compare(pdf, items)


def _habit_row(item: dict[str, Any]) -> list[Any]:
    """A counter's facts as a table row."""
    low, high = item.get("lowest") or {}, item.get("highest") or {}
    return [
        item["label"],
        f"{item['days_with_data']} / {item['days']}",
        item.get("total"),
        item.get("mean"),
        item.get("median"),
        _extreme(low),
        _extreme(high),
    ]


def _extreme(found: dict[str, Any]) -> str:
    """« 6 (2026-09-04) »."""
    if not found:
        return "-"
    return f"{pdf_blocks.cell_text(float(found['value']))} ({found['date']})"


def _bars(pdf: FPDF, item: dict[str, Any]) -> None:
    """Cigarettes per day over the period; a day without data stays empty."""
    series = {date.fromisoformat(d): v for d, v in item.get("series") or []}
    if len(series) < 2:  # noqa: PLR2004
        return
    if pdf.get_y() + _CHART_H + 12 > pdf.h - pdf.b_margin:
        pdf.add_page()
    heading(pdf, "Cigarettes par jour", 10)
    first, last = min(series), max(series)
    top = max(series.values()) or 1
    x, y, w = pdf.l_margin, pdf.get_y(), pdf.epw
    step = w / ((last - first).days + 1)
    pdf.set_fill_color(37, 99, 235)
    for day, value in series.items():
        h = value / top * _CHART_H
        left = x + (day - first).days * step
        pdf.rect(left, y + _CHART_H - h, max(step * 0.8, 0.3), h, "F")
    pdf.set_font("Helvetica", size=7)
    pdf.set_xy(x, y + _CHART_H + 1)
    pdf.cell(w, 4, f"{first} -> {last}  -  max {top:g} / jour")
    pdf.set_fill_color(255, 255, 255)
    pdf.ln(6)


def _periods(pdf: FPDF, item: dict[str, Any]) -> None:
    """The cigarettes per week or month: days recorded, mean, total."""
    periods = item.get("periods") or []
    unit = "Semaine du" if periods and periods[0]["unit"] == "week" else "Mois"
    rows = [
        [p["start"], p["days_with_data"], p["mean"], p["total"]]
        for p in periods
    ]
    head = [unit, "Jours saisis", "Moy./jour saisi", "Total"]
    pdf_blocks.table(pdf, "Cigarettes par période", head, rows)


def _compare(pdf: FPDF, items: list[dict[str, Any]]) -> None:
    """Before / after the chosen day, per counter."""
    rows = []
    for item in items:
        found = item.get("compare")
        if not found:
            continue
        before, after = found["before"], found["after"]
        change = found["change_pct"]
        rows.append(
            [
                item["label"],
                f"{before.get('mean', '-')} ({before['days_with_data']} j)",
                f"{after.get('mean', '-')} ({after['days_with_data']} j)",
                "-" if change is None else f"{change:+g} %",
            ]
        )
    if rows:
        split = items[0].get("compare", {}).get("split", "")
        head = ["Compteur", f"Avant le {split}", "Depuis", "Évolution"]
        pdf_blocks.table(
            pdf, "Avant / après (moyenne par jour saisi)", head, rows
        )


def _medications(pdf: FPDF, items: list[dict[str, Any]]) -> None:
    """Adherence per treatment."""
    rows = [_dose_row(i) for i in items]
    head = [
        "Traitement",
        "Du -> au",
        "Prévu / pris / non pris",
        "Observance",
        "Sans saisie · plus long trou",
        "Heure habituelle",
        "Saisies après coup",
    ]
    pdf_blocks.table(
        pdf,
        "Médicaments - observance",
        head,
        rows,
        [0.2, 0.16, 0.14, 0.1, 0.16, 0.1, 0.14],
    )


def _dose_row(item: dict[str, Any]) -> list[Any]:
    """One treatment's adherence as a table row."""
    per_day = (
        f" ({item['doses_per_day']}/j)" if item.get("doses_per_day") else ""
    )
    planned = item.get("planned")
    rate = item.get("rate")
    return [
        f"{item['name']}{per_day}",
        f"{item['start']} -> {item['end']}",
        f"{'-' if planned is None else planned} / {item['taken']} / "
        f"{item['skipped']}",
        "à la demande" if rate is None else f"{rate:g} %",
        f"{item['days_without_record']} j · {item['longest_gap_days']} j",
        item.get("usual_time") or "-",
        item.get("entered_late", 0),
    ]


def _meals(pdf: FPDF, found: dict[str, Any]) -> None:
    """What was eaten, as recorded and read."""
    if not found:
        return
    heading(pdf, "Alimentation")
    pdf.set_font("Helvetica", size=9)
    for text in _meal_lines(found):
        line(pdf, 5, text)
    rows = [
        [f["name"], f["meals"], f["grams"]]
        for f in found.get("top_foods") or []
    ]
    pdf_blocks.table(
        pdf,
        "Mes aliments les plus mangés",
        ["Aliment", "Repas", "Grammes"],
        rows,
    )
    months = [
        [m["start"][:7], m["meals"], m["analysed_days"], m["energy_kcal"]]
        for m in found.get("months") or []
    ]
    head = ["Mois", "Repas", "Jours lus", "Énergie moy. (kcal/j)"]
    pdf_blocks.table(pdf, "Par mois", head, months)


def _meal_lines(found: dict[str, Any]) -> list[str]:
    """The meals' summary lines."""
    meals = found["meals"]
    share = round(found["analysed"] / meals * 100) if meals else 0
    types = ", ".join(
        f"{_MEALS_FR.get(k, k)} {v}" for k, v in found["by_type"].items()
    )
    lines = [
        f"{meals} repas sur {found['days_with_meals']} jours ; lus par "
        f"l'IA : {found['analysed']} ({share} %) ; avec photo : "
        f"{found['with_photo']} ; saisis plus de 3 h après : "
        f"{found['entered_late']}.",
        f"Par type : {types}",
    ]
    if found.get("sources"):
        lines.append("Valeurs : " + _channels(found["sources"]))
    return (
        lines
        + _means_line(found.get("daily_means") or {})
        + _score_line(found.get("scores") or {})
    )


def _means_line(means: dict[str, Any]) -> list[str]:
    """The daily means over the days with a read meal."""
    if not means:
        return []
    return [
        f"Moyenne par jour ({means['days']} jours lus) : "
        f"{means['energy_kcal']:g} kcal, protéines {means['protein_g']:g} g, "
        f"glucides {means['carbs_g']:g} g (sucres {means['sugars_g']:g}), "
        f"lipides {means['fat_g']:g} g (saturés {means['sat_fat_g']:g}), "
        f"fibres {means['fiber_g']:g} g, sodium {means['sodium_mg']:g} mg."
    ]


def _score_line(scores: dict[str, Any]) -> list[str]:
    """The AI scores: mean, range, bands."""
    if not scores:
        return []
    return [
        f"Note IA : moyenne {scores['mean']:g}/10 (de {scores['lowest']:g} "
        f"à {scores['highest']:g}) ; " + _channels(scores["bands"])
    ]


def _timing(pdf: FPDF, title: str, found: dict[str, Any]) -> None:
    """Doses or meals: entered at the time, the same day, later."""
    if not found:
        return
    window = f"{found['window_hours']:g} h"
    via = (
        f" ; canaux : {_channels(found['channels'])}"
        if found.get("channels")
        else ""
    )
    line(
        pdf,
        5,
        f"{title} : {found['entries']} saisies ; dans les {window} : "
        f"{found['at_the_time']} ; le jour même : {found['same_day']} ; après "
        f"coup : {found['later']}{via}.",
    )


def _channels(counts: dict[str, Any]) -> str:
    """« site 12, raccourci 30 »."""
    return ", ".join(f"{k} {v}" for k, v in counts.items()) or "-"
