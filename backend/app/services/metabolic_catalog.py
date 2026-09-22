"""Reference tables for the metabolic markers (data, not logic).

Each marker lists its inputs, formula and published reference bands.
Long lines are allowed here (sources and thresholds read better whole).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import NamedTuple

from app.services import biology_catalog as bio
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
    #: Input whose direct measurement outranks this indirect score.
    superseded_by: str | None = None


def age(birth_year: float) -> float:
    """Approximate age in years from the birth year."""
    return float(date.today().year - int(birth_year))


_SENIOR_AGE = 65.0


def band_for(spec: Spec, values: dict[str, float], value: float) -> Band:
    """Reference band containing ``value`` (age-adjusted when defined)."""
    senior = "birth_year" in values and age(values["birth_year"]) >= _SENIOR_AGE
    bands = spec.senior_bands if spec.senior_bands and senior else spec.bands
    return next(band for band in bands if value < band.below)


#: FibroScan (transient elastography) metric keys.
CAP_KEY = "liver.cap"
LSM_KEY = "liver.lsm"

#: Inputs → metric keys (first match by most recent date wins).
SOURCES: dict[str, tuple[str, ...]] = {
    "cap": (CAP_KEY,),
    "lsm": (LSM_KEY,),
    "waist": ("body.waist", "apple.waist_circumference"),
    "height": ("body.height",),
    "weight": ("body.weight",),
    "birth_year": ("profile.birth_year",),
    "tg": (bio.metric_key("triglycerides"),),
    "ggt": (bio.metric_key("ggt"),),
    "ast": (bio.metric_key("asat"),),
    "alt": (bio.metric_key("alat"),),
    "platelets": (bio.metric_key("plaquettes"),),
    "glucose": (bio.metric_key("glycemie"),),
    "hba1c": (bio.metric_key("hba1c"),),
}

#: Display unit of each input (after unit normalization).
UNITS = {
    "cap": "dB/m",
    "lsm": "kPa",
    "waist": "cm",
    "height": "cm",
    "weight": "kg",
    "birth_year": "",
    "tg": "g/L",
    "ggt": "U/L",
    "ast": "U/L",
    "alt": "U/L",
    "platelets": "G/L",
    "glucose": "g/L",
    "hba1c": "%",
}

#: Inputs that do not go stale (not used for the marker's date).
STATIC = frozenset({"height", "birth_year"})

#: Inputs whose dates are events worth a history point (a lab report, a
#: FibroScan, a tape measure) — weight is daily, so only looked up.
EVENTS = frozenset(
    {
        "waist",
        "tg",
        "ggt",
        "ast",
        "alt",
        "platelets",
        "glucose",
        "hba1c",
        "cap",
        "lsm",
    }
)

#: Inputs that must come from a lab / explicit entry: Apple glucose shares
#: the ``bio.glycemie`` field, but a sensor reading is not a fasting value.
LAB_ONLY = frozenset({"glucose"})
LAB_SOURCES = frozenset({"biology", "document", "document-ai", "manual", "cda"})

#: How old a looked-up input may be for a past marker value (days).
MAX_AGE = {"weight": 30, "waist": 120}
DEFAULT_MAX_AGE = 400

LABELS = {
    "cap": "CAP FibroScan",
    "lsm": "Élasticité FibroScan",
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
    "cap_db_m": MetricSpec(CAP_KEY, "CAP FibroScan (graisse du foie)", "liver", "float", "dB/m", "last"),
    "lsm_kpa": MetricSpec(LSM_KEY, "Élasticité FibroScan (fibrose)", "liver", "float", "kPa", "last"),
}

SPECS: tuple[Spec, ...] = (
    Spec(
        "cap", "FibroScan — CAP (graisse du foie)", "dB/m", ("cap",),
        lambda v: v["cap"],
        (
            Band(248, "ok", "S0 : pas de stéatose significative"),
            Band(268, "warn", "S1 : stéatose légère"),
            Band(280, "high", "S2 : stéatose modérée"),
            Band(_INF, "high", "S3 : stéatose sévère"),
        ),
        "Mesure directe · S1 ≥ 248 · S2 ≥ 268 · S3 ≥ 280 dB/m (Karlas 2017)", 0,
    ),
    Spec(
        "lsm", "FibroScan — élasticité (fibrose)", "kPa", ("lsm",),
        lambda v: v["lsm"],
        (
            Band(8, "ok", "Fibrose avancée peu probable"),
            Band(12, "warn", "Zone grise : avis hépatologique"),
            Band(15, "high", "Fibrose avancée probable"),
            Band(_INF, "high", "Maladie chronique avancée du foie possible"),
        ),
        "Mesure directe · < 8 exclut · 8–12 intermédiaire · ≥ 12 fibrose avancée probable · ≥ 15 maladie avancée (EASL 2024, Baveno VII) · sonde XL si IMC ≥ 30", 1,
    ),
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
        superseded_by="cap",
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
        superseded_by="lsm",
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
