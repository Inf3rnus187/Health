"""A meal's nutrients against official daily references, by meal type.

The references are those of an adult-type, not a person's own needs:

- energy, protein, carbohydrate, sugars, fat, saturates: the reference
  intakes of Regulation (EU) 1169/2011, Annex XIII part B (2 000 kcal);
- fibre: 30 g a day, ANSES 2016 (« apport satisfaisant »);
- sodium: under 2 000 mg a day, WHO (5 g of salt).

The part of the day a meal carries is only indicative: the ANSES sheet
« Veiller à son équilibre nutritionnel » gives breakfast 15–25 % and
lunch or dinner 30–40 % each; ANSES (2019) could not recommend any split
and gives none for a snack, which then only gets its share of the day.
Computed by code on each read, never by a model.
"""

from __future__ import annotations

from typing import Any

#: key → (value a day, unit, kind, source). ``limit``: not to exceed;
#: ``target``: to reach; ``reference``: neither, a benchmark.
DAILY: dict[str, tuple[float, str, str, str]] = {
    "energy_kcal": (2000, "kcal", "reference", "UE"),
    "protein_g": (50, "g", "reference", "UE"),
    "carbs_g": (260, "g", "reference", "UE"),
    "sugars_g": (90, "g", "limit", "UE"),
    "fat_g": (70, "g", "reference", "UE"),
    "sat_fat_g": (20, "g", "limit", "UE"),
    "fiber_g": (30, "g", "target", "ANSES"),
    "sodium_mg": (2000, "mg", "limit", "OMS"),
}

#: The indicative part of the day, in %, of each meal type.
SHARES: dict[str, tuple[int, int]] = {
    "breakfast": (15, 25),
    "lunch": (30, 40),
    "dinner": (30, 40),
}

SOURCES: dict[str, dict[str, str]] = {
    "UE": {
        "name": "Règlement (UE) n° 1169/2011, annexe XIII partie B : "
        "apports de référence pour un adulte-type (8 400 kJ / 2 000 kcal)",
        "url": "https://eur-lex.europa.eu/legal-content/FR/ALL/"
        "?uri=celex%3A32011R1169",
    },
    "ANSES": {
        "name": "ANSES 2016, actualisation des repères du PNNS : "
        "fibres 30 g par jour",
        "url": "https://www.anses.fr/fr/system/files/NUT2012SA0103Ra-1.pdf",
    },
    "OMS": {
        "name": "OMS : moins de 2 g de sodium par jour (5 g de sel)",
        "url": "https://www.who.int/fr/news-room/fact-sheets/detail/"
        "sodium-reduction",
    },
    "repas": {
        "name": "ANSES, « Veiller à son équilibre nutritionnel » : "
        "petit-déjeuner 15–25 %, déjeuner et dîner 30–40 % de la journée "
        "(indicatif : en 2019 l’ANSES n’a pu recommander aucune "
        "répartition ; rien pour une collation)",
        "url": "https://www.anses.fr/fr/system/files/NUT-fi-EquilibreNut.pdf",
    },
}


def compare(analysis: Any, meal_type: str) -> dict[str, Any] | None:
    """The meal's totals against the day's references and its meal's part.

    Each row: ``day`` (the reference a day), ``unit``, ``kind``,
    ``source``, ``day_pct`` (the meal's share of it) and, for a meal
    type with a part (not a snack), ``low``/``high`` (that part) and
    ``verdict`` (below, within, above). None without totals.
    """
    totals = analysis.get("totals") if isinstance(analysis, dict) else None
    if not isinstance(totals, dict):
        return None
    share = SHARES.get(meal_type)
    rows = {key: _row(key, totals.get(key), share) for key in DAILY}
    return {
        "meal_type": meal_type,
        "share_pct": list(share) if share else None,
        "rows": {key: row for key, row in rows.items() if row},
    }


def table() -> dict[str, Any]:
    """Every reference, the meal parts and their sources."""
    return {
        "daily": {
            key: {"value": day, "unit": unit, "kind": kind, "source": src}
            for key, (day, unit, kind, src) in DAILY.items()
        },
        "share_pct": {kind: list(part) for kind, part in SHARES.items()},
        "sources": SOURCES,
        "note": "Repères d’un adulte-type, pas des besoins personnels "
        "(âge, sexe, poids, activité, traitement).",
    }


def _row(
    key: str, value: Any, share: tuple[int, int] | None
) -> dict[str, Any] | None:
    """One nutrient against its reference, or None when not a number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    day, unit, kind, source = DAILY[key]
    row: dict[str, Any] = {
        "day": day,
        "unit": unit,
        "kind": kind,
        "source": source,
        "day_pct": round(value / day * 100),
    }
    if share:
        low, high = (round(day * part / 100, 1) for part in share)
        row |= {"low": low, "high": high, "verdict": _verdict(value, low, high)}
    return row


def _verdict(value: float, low: float, high: float) -> str:
    """Where the meal falls against its part of the day."""
    if value < low:
        return "below"
    return "above" if value > high else "within"
