"""Work ↔ health report: traces (what third parties saw) and expenses."""

from __future__ import annotations

from datetime import date
from typing import Any

from fpdf import FPDF

from app.services.pdf_blocks import table
from app.services.pdf_text import heading, line

#: Short trace names for the day-by-day journal.
SHORT = {
    "transport": "transp.",
    "taxi": "taxi",
    "parking": "parking",
    "livraison": "livr.",
    "repas": "repas",
    "hotel": "hôtel",
    "frais": "frais",
    "activite": "tickets",
}
_MONTH_KINDS = (
    "livraison",
    "repas",
    "taxi",
    "transport",
    "parking",
    "hotel",
    "frais",
)


_MONTH_HEAD = ["Mois", "Livr.", "Repas", "Taxi", "Transp.", "Parking",
               "Hôtel", "Frais", "Total"]  # fmt: skip
_INTRO = (
    "Traces : ce que des tiers ont enregistré (transport, taxi, parking, "
    "repas livrés, hôtel, notes de frais)."
)


def traces(pdf: FPDF, data: dict[str, Any]) -> None:
    """Traces by kind, presence without clocking, late traces, spending."""
    tr = data["traces"]
    if not tr["by_kind"]:
        return
    heading(pdf, "Traces et dépenses")
    line(pdf, 5, _INTRO)
    kinds = [[k["label"], k["count"], k["total"]] for k in tr["by_kind"]]
    table(pdf, "Par type", ["Type", "Nombre", "Montant (EUR)"], kinds,
          [0.5, 0.2, 0.3])  # fmt: skip
    for text in _facts(tr):
        line(pdf, 5, text)
    months = [
        [m["month"], *(m.get(k) for k in _MONTH_KINDS), m["total"]]
        for m in tr["months"]
    ]
    table(pdf, "Dépenses par mois (EUR)", _MONTH_HEAD, months)


def cell(traces_of_day: list[dict[str, Any]]) -> str:
    """A day's traces in a few words for the journal."""
    parts = []
    for t in traces_of_day[:3]:
        when = t["time"] or "(jour)"
        span = f"{when}-{t['end']}" if t["end"] else when
        price = f" {t['amount']:g}EUR" if t["amount"] else ""
        parts.append(f"{SHORT.get(t['kind'], t['kind'])} {span}{price}")
    more = len(traces_of_day) - 3
    return ", ".join(parts) + (f" +{more}" if more > 0 else "")


def _facts(tr: dict[str, Any]) -> list[str]:
    """Presence without clocking, late traces, what meals cost."""
    d = tr["deliveries"]
    return [
        f"Jours sans pointage où une trace vous place quelque part ou "
        f"montre votre activité (tickets) : "
        f"{len(tr['unclocked_days'])} ({_dates(tr['unclocked_days'])}).",
        f"Traces après 21 h un jour travaillé : {len(tr['late'])} ("
        + ", ".join(
            f"{_d(x['date'])} {x['time']} {SHORT.get(x['kind'], '')}"
            for x in tr["late"][:10]
        )
        + ").",
        f"Repas livrés ou achetés : {d['orders']} pour {d['total']:g} EUR, "
        f"dont {d['late']} après 21 h et {d['on_long_days']} les jours longs "
        "(plus de 10 h ou débauche après 21 h) pour "
        f"{d['long_days_total']:g} EUR.",
        "Note moyenne de ces repas (analyse IA, sur 10) : "
        + ("-" if d["avg_score"] is None else f"{d['avg_score']:g}")
        + ".",
        "Heures travaillées / dépense repas du jour : "
        + _corr(d["hours_vs_spend"]),
    ]


def _corr(corr: dict[str, Any] | None) -> str:
    """A correlation in a few words."""
    if corr is None:
        return "pas assez de jours."
    return f"r = {corr['r']:+.2f} sur {corr['n']} jours."


def _dates(days: list[date]) -> str:
    """The first dates of a list."""
    return ", ".join(_d(d) for d in days[:12]) or "aucun"


def _d(day: date) -> str:
    """A date as ``02/03/2026``."""
    return f"{day:%d/%m/%Y}"
