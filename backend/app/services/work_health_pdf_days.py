"""The report's « Journées les plus significatives » table.

One line per day that stands out (:mod:`work_highlights`): arrival,
departure (« +1 » the next day), amplitude, and why — a continuous
session, an amplitude over 13 h, a weekend or public holiday worked,
work during an absence, a late end — with the notes typed that day.
"""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

from app.services.pdf_blocks import table
from app.services.pdf_text import line
from app.services.work_highlights import hm

_DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
         "dimanche")  # fmt: skip


def significant(pdf: FPDF, data: dict[str, Any]) -> None:
    """The most significant days, the most striking first."""
    rows = data.get("highlights") or []
    if not rows:
        return
    table(
        pdf,
        "Journées les plus significatives",
        ["Date", "Arrivée", "Départ", "Amplitude", "Pourquoi, et notes"],
        [_row(r) for r in rows],
        [0.17, 0.09, 0.1, 0.1, 0.54],
    )
    pdf.set_font("Helvetica", "I", 8)
    line(
        pdf,
        4,
        "Amplitude : de la première embauche à la dernière débauche du "
        "jour (pauses comprises) ; « +1 » : le lendemain. Heures des "
        "sessions pointées, importées ou complétées (voir la méthode).",
    )
    pdf.set_font("Helvetica", size=10)


def _row(r: dict[str, Any]) -> list[Any]:
    """One day: when, from / to, how long, why."""
    worked = r["hours"] or 0
    span = hm(r["amplitude"])
    if worked and abs(worked - r["amplitude"]) >= 0.02:  # noqa: PLR2004
        span += f" (travail {hm(worked)})"
    why = [*r["flags"], *(f"note : {n}" for n in r["notes"])]
    if r.get("remote"):
        why.append(f"dont {hm(r['remote'])} à distance")
    return [
        f"{r['date']:%d/%m/%Y} ({_DAYS[r['weekday']]})",
        r["arrival"],
        r["departure"],
        span,
        " ; ".join(why),
    ]
