"""Work ↔ health report, second half: sleep, periods, absences, journal.

The evidence annex embeds the images and prints every file's SHA-256.
"""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from fpdf import FPDF

from app.services import work_health_pdf_traces
from app.services.pdf_blocks import table
from app.services.pdf_text import heading, line
from app.services.work_legal import holidays
from app.services.work_math import clock_text

_BLUE, _ORANGE = (37, 99, 235), (234, 88, 12)
_READINGS = {
    "hours_vs_sleep": (
        "heures travaillées",
        "durée du sommeil la nuit suivante",
    ),
    "hours_vs_awakenings": ("heures travaillées", "réveils la nuit suivante"),
    "end_vs_sleep": ("heure de débauche", "durée du sommeil la nuit suivante"),
}
#: |r| below → strength.
_STRENGTH = ((0.1, "négligeable"), (0.3, "faible"), (0.5, "modérée"))
_PERIOD_HEAD = [
    "Période",
    "Jours",
    "Heures",
    "Sup.",
    "Nuits",
    "Sommeil h",
    "Réveils",
    "FC repos",
    "VFC",
    "Cig./j",
    "Cafés/j",
]


def sleep(pdf: FPDF, data: dict[str, Any]) -> None:
    """Correlations in plain words, the night-after bands, the chart."""
    heading(pdf, "Travail et sommeil")
    for key, corr in data["sleep"]["correlations"].items():
        line(pdf, 5, _reading(key, corr))
    line(
        pdf,
        5,
        "Une corrélation décrit un lien dans les données ; elle ne "
        "prouve pas à elle seule une cause.",
    )
    table(
        pdf,
        "Sommeil la nuit suivante, selon la journée",
        ["Journée", "Nuits", "Sommeil moyen (h)", "Réveils", "Blocs"],
        [
            [
                b["label"],
                b["nights"],
                b["sleep_hours"],
                b["awakenings"],
                b["blocks"],
            ]
            for b in data["sleep"]["bands"]
        ],
    )
    _chart(pdf, data["weeks"][-52:])


def periods(pdf: FPDF, data: dict[str, Any]) -> None:
    """Years, months and weeks: work, sleep and health side by side."""
    widths = [0.12] + [0.088] * 10
    for title, key in (
        ("Par année", "years"),
        ("Par mois", "months"),
        ("Par semaine", "weeks"),
    ):
        table(pdf, title, _PERIOD_HEAD, [_period(p) for p in data[key]], widths)


def _span(a: dict[str, Any]) -> str:
    """« Arrêt maladie du 07/05/2026 après-midi au 09/05/2026 (2,5 jours) »."""
    first = " après-midi" if a.get("start_half") == "pm" else ""
    last = " midi" if a.get("end_half") == "am" else ""
    return (
        f"{a['label']} du {_d(a['start_date'])}{first} au "
        f"{_d(a['end_date'])}{last} ({a['days']:g} jours)"
    )


def absences(pdf: FPDF, data: dict[str, Any]) -> None:
    """Each absence with the work done and the evidence logged inside it."""
    if not data["absences"]:
        return
    heading(pdf, "Arrêts et absences")
    for a in data["absences"]:
        pdf.set_font("Helvetica", "B", 10)
        line(pdf, 6, _span(a))
        pdf.set_font("Helvetica", size=10)
        for text in (
            f"Cause : {a['cause'] or '-'}",
            a["note"],
            f"Travail pendant l'absence : {len(a['worked_days'])} jours "
            f"({', '.join(_d(d) for d in a['worked_days'][:15]) or 'aucun'}), "
            f"{a['worked_hours']:g} h pointées.",
            f"Preuves datées pendant l'absence : {a['evidence']} ; appels : "
            f"{a['calls']} (dont {a['calls_on_sundays']} un dimanche) ; "
            f"traces (transport, taxi, parking, repas…) : {a['traces']}.",
        ):
            if text:
                line(pdf, 5, text)


def journal(pdf: FPDF, data: dict[str, Any]) -> None:
    """Every worked or absent day, with the night after it."""
    rows = [
        r for r in data["days"] if r["worked"] or r["absence"] or r["traces"]
    ]
    feasts = {d for y in {r["date"].year for r in rows} for d in holidays(y)}
    table(
        pdf,
        "Journal jour par jour",
        [
            "Date",
            "Embauche",
            "Débauche",
            "Heures",
            "Remarque",
            "Traces",
            "Sommeil après",
            "Réveils",
            "Blocs",
        ],
        [_day(r, feasts) for r in rows],
        [0.12, 0.08, 0.08, 0.07, 0.15, 0.25, 0.09, 0.08, 0.08],
    )


def evidence(pdf: FPDF, data: dict[str, Any], images: dict[str, bytes]) -> None:
    """The evidence annex, oldest first, images shown."""
    if not data["evidence"]:
        return
    pdf.add_page()
    heading(pdf, "Annexe : preuves")
    for item in data["evidence"]:
        _item(pdf, item, images.get(item["id"]))


def _item(pdf: FPDF, item: dict[str, Any], image: bytes | None) -> None:
    """One proof: when, what, how many, its file and fingerprint."""
    pdf.set_font("Helvetica", "B", 10)
    count = f" (x{item['count']})" if item["count"] > 1 else ""
    line(
        pdf,
        6,
        f"{item['occurred_at']:%d/%m/%Y %H:%M} - {item['label']}{count} - "
        f"{item['title']}",
    )
    pdf.set_font("Helvetica", size=9)
    if item["description"]:
        line(pdf, 5, item["description"])
    if item["during_absence"]:
        line(pdf, 5, "Pendant une absence.")
    if item["file_name"]:
        name, digest = item["file_name"], item["sha256"]
        line(pdf, 5, f"Fichier : {name} - SHA-256 : {digest}")
    _image(pdf, image)
    pdf.set_font("Helvetica", size=10)


def _reading(key: str, corr: dict[str, Any] | None) -> str:
    """A correlation in plain French."""
    what, against = _READINGS[key]
    if corr is None:
        return (
            f"{what.capitalize()} / {against} : pas assez de nuits appariées."
        )
    r = corr["r"]
    size = abs(r)
    strength = next(
        (word for limit, word in _STRENGTH if size < limit), "forte"
    )
    way = (
        "quand l'un augmente, l'autre baisse"
        if r < 0
        else "ils augmentent ensemble"
    )
    return (
        f"{what.capitalize()} / {against} : r = {r:+.2f} sur {corr['n']} "
        f"jours, corrélation {strength} ({way})."
    )


def _chart(pdf: FPDF, weeks: list[dict[str, Any]]) -> None:
    """Weekly hours (bars) and average sleep per night (line, x5)."""
    if not weeks:
        return
    heading(pdf, "Heures par semaine et sommeil moyen")
    box = (pdf.l_margin, pdf.get_y() + 2, pdf.epw, 50.0)
    top = max([60.0] + [p["hours"] for p in weeks])
    _bars(pdf, box, top, [p["hours"] for p in weeks])
    _sleep_line(pdf, box, top, [p["sleep_hours"] for p in weeks])
    pdf.set_y(box[1] + box[3] + 2)
    line(
        pdf,
        4,
        "Barres bleues : heures travaillées. Ligne orange : sommeil moyen "
        "par nuit (x5 pour l'échelle).",
    )


def _bars(
    pdf: FPDF, box: tuple[float, ...], top: float, values: list[float]
) -> None:
    """One blue bar per week."""
    x, y, w, h = box
    step = w / len(values)
    pdf.set_fill_color(*_BLUE)
    for i, value in enumerate(values):
        bar = value / top * h
        left = x + i * step + 0.3
        pdf.rect(left, y + h - bar, max(step - 0.6, 0.4), bar, "F")


def _sleep_line(
    pdf: FPDF, box: tuple[float, ...], top: float, values: list[float | None]
) -> None:
    """The weekly sleep average as an orange line (hours x5)."""
    x, y, w, h = box
    step = w / len(values)
    points = [
        (x + (i + 0.5) * step, y + h - v * 5 / top * h)
        for i, v in enumerate(values)
        if v is not None
    ]
    pdf.set_draw_color(*_ORANGE)
    for (x1, y1), (x2, y2) in zip(points, points[1:], strict=False):
        pdf.line(x1, y1, x2, y2)
    pdf.set_draw_color(0, 0, 0)


def _period(p: dict[str, Any]) -> list[Any]:
    """One period row."""
    return [
        p["period"],
        p["days_worked"],
        p["hours"],
        p["overtime"],
        p["nights"],
        p["sleep_hours"],
        p["awakenings"],
        p["rest.hr"],
        p["heart.hrv"],
        p["habit.cigarettes"],
        p["habit.coffee"],
    ]


def _absence_note(row: dict[str, Any]) -> str:
    """« absence », or « demi-journée d'absence »."""
    if not row["absence"]:
        return ""
    half = row.get("absence_share", 1) < 1
    return "demi-journée d'absence" if half else "absence"


def _day(row: dict[str, Any], feasts: set[date]) -> list[Any]:
    """One journal row."""
    night = row["night"] or {}
    remote = row.get("remote")
    notes = [
        f"dont {remote:g} h à distance" if remote else "",
        "incomplète" if row["partial"] else "",
        _absence_note(row),
        "dimanche" if row["weekday"] == 6 else "",  # noqa: PLR2004
        "férié" if row["date"] in feasts else "",
    ]
    asleep = night.get("asleep_min")
    return [
        _d(row["date"]),
        clock_text(row["start"]),
        clock_text(row["end"]),
        row["hours"],
        ", ".join(n for n in notes if n),
        work_health_pdf_traces.cell(row["traces"]),
        None if asleep is None else round(asleep / 60, 1),
        night.get("awakenings"),
        night.get("blocks"),
    ]


def _image(pdf: FPDF, data: bytes | None) -> None:
    """Embed an image (PNG, JPEG, GIF); other formats are listed only."""
    if not data:
        return
    try:
        pdf.image(io.BytesIO(data), w=min(pdf.epw, 120))
    except Exception:  # noqa: BLE001 - HEIC and others cannot be embedded
        line(pdf, 5, "(image non affichable ici ; fichier conservé)")


def _d(day: date) -> str:
    """A date as ``02/03/2026``."""
    return f"{day:%d/%m/%Y}"
