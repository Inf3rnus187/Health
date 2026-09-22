"""Reference tables for the metabolic markers (data, not logic).

Each marker lists its inputs, formula and published reference bands.
Long lines are allowed here (sources and thresholds read better whole).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import NamedTuple

from app.services import metabolic_scores as score
from app.services.apple_health.spec import MetricSpec

_INF = float("inf")


class Band(NamedTuple):
    """Values strictly below ``below`` get this level and text."""

    below: float
    level: str
    text: str


class Spec(NamedTuple):
    """How to compute and interpret one marker."""

    key: str
    label: str
    unit: str
    needs: tuple[str, ...]
    compute: Callable[[dict[str, float]], float]
    bands: tuple[Band, ...]
    reference: str
    digits: int
    senior_bands: tuple[Band, ...] | None = None


def age(birth_year: float) -> float:
    """Approximate age in years from the birth year."""
    return float(date.today().year - int(birth_year))


#: Inputs → metric keys (first match by most recent date wins).
SOURCES: dict[str, tuple[str, ...]] = {
    "waist": ("body.waist", "apple.waist_circumference"),
    "height": ("body.height",),
    "weight": ("body.weight",),
    "birth_year": ("profile.birth_year",),
    "tg": ("triglycerides",),
    "ggt": ("ggt",),
    "ast": ("asat",),
    "alt": ("alat",),
    "platelets": ("plaquettes",),
    "glucose": ("glycemie",),
    "hba1c": ("hba1c",),
}

#: Inputs that do not go stale (not used for the marker's date).
STATIC = frozenset({"height", "birth_year"})

LABELS = {
    "waist": "Tour de taille",
    "height": "Taille",
    "weight": "Poids",
    "birth_year": "Année de naissance",
    "tg": "Triglycérides",
    "ggt": "GGT",
    "ast": "ASAT",
    "alt": "ALAT",
    "platelets": "Plaquettes",
    "glucose": "Glycémie à jeun",
    "hba1c": "HbA1c",
}

# fmt: off
#: Profile fields entered in the web form → metric created on first use.
PROFILE: dict[str, MetricSpec] = {
    "waist_cm": MetricSpec("body.waist", "Tour de taille", "body", "float", "cm", "last"),
    "height_cm": MetricSpec("body.height", "Taille", "body", "float", "cm", "last"),
    "birth_year": MetricSpec("profile.birth_year", "Année de naissance", "profile", "int", None, "last"),
}

SPECS: tuple[Spec, ...] = (
    Spec(
        "whtr", "Tour de taille / taille (WHtR)", "", ("waist", "height"),
        lambda v: score.whtr(v["waist"], v["height"]),
        (
            Band(0.5, "ok", "Risque cardiométabolique faible"),
            Band(0.6, "warn", "Risque accru : excès de graisse abdominale"),
            Band(_INF, "high", "Risque élevé : graisse abdominale importante"),
        ),
        "< 0,5 faible · 0,5–0,6 accru · ≥ 0,6 élevé (Ashwell)", 2,
    ),
    Spec(
        "bmi", "Indice de masse corporelle (IMC)", "kg/m²", ("weight", "height"),
        lambda v: score.bmi(v["weight"], v["height"]),
        (
            Band(18.5, "warn", "Maigreur"),
            Band(25, "ok", "Corpulence normale"),
            Band(30, "warn", "Surpoids"),
            Band(_INF, "high", "Obésité"),
        ),
        "18,5–25 normal · 25–30 surpoids · ≥ 30 obésité (OMS) — reflète mal la graisse viscérale", 1,
    ),
    Spec(
        "fli", "Fatty Liver Index (stéatose)", "/100", ("tg", "weight", "height", "ggt", "waist"),
        lambda v: score.fli(v["tg"], score.bmi(v["weight"], v["height"]), v["ggt"], v["waist"]),
        (
            Band(30, "ok", "Stéatose hépatique peu probable"),
            Band(60, "warn", "Zone intermédiaire : ni exclue ni confirmée"),
            Band(_INF, "high", "Stéatose hépatique probable"),
        ),
        "< 30 exclut · 30–60 indéterminé · ≥ 60 probable (Bedogni 2006)", 0,
    ),
    Spec(
        "fib4", "FIB-4 (fibrose du foie)", "", ("birth_year", "ast", "alt", "platelets"),
        lambda v: score.fib4(age(v["birth_year"]), v["ast"], v["alt"], v["platelets"]),
        (
            Band(1.30, "ok", "Fibrose avancée peu probable"),
            Band(2.67, "warn", "Zone grise : FibroScan / avis médical conseillé"),
            Band(_INF, "high", "Fibrose avancée possible : avis hépatologique"),
        ),
        "< 1,30 (< 2,0 dès 65 ans) exclut · ≥ 2,67 élevé (EASL / AFEF)", 2,
        (
            Band(2.0, "ok", "Fibrose avancée peu probable"),
            Band(2.67, "warn", "Zone grise : FibroScan / avis médical conseillé"),
            Band(_INF, "high", "Fibrose avancée possible : avis hépatologique"),
        ),
    ),
    Spec(
        "hba1c", "Hémoglobine glyquée (HbA1c)", "%", ("hba1c",),
        lambda v: v["hba1c"],
        (
            Band(5.7, "ok", "Normale"),
            Band(6.5, "warn", "Prédiabète"),
            Band(_INF, "high", "Zone diabète : à confirmer / suivre avec le médecin"),
        ),
        "< 5,7 % normal · 5,7–6,4 % prédiabète · ≥ 6,5 % diabète · objectif fréquent ≤ 7 % si diabète traité", 1,
    ),
    Spec(
        "glycemie", "Glycémie à jeun", "g/L", ("glucose",),
        lambda v: v["glucose"],
        (
            Band(1.10, "ok", "Normale"),
            Band(1.26, "warn", "Hyperglycémie modérée à jeun"),
            Band(_INF, "high", "Zone diabète si confirmée à 2 reprises"),
        ),
        "< 1,10 normal · 1,10–1,25 intermédiaire · ≥ 1,26 g/L diabète (OMS / HAS)", 2,
    ),
    Spec(
        "tyg", "Indice TyG (insulinorésistance)", "", ("tg", "glucose"),
        lambda v: score.tyg(v["tg"], v["glucose"]),
        (
            Band(8.5, "ok", "Pas d'insulinorésistance évidente"),
            Band(8.8, "warn", "Insulinorésistance possible"),
            Band(_INF, "high", "Insulinorésistance probable"),
        ),
        "Indicatif : seuils non consensuels (≈ 8,5–8,8)", 2,
    ),
)
# fmt: on
