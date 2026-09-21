"""Curated catalog of French lab analytes.

A blood-test PDF lists analytes in many layouts — name on its own line,
method lines in parentheses, ``percentage then absolute`` rows, the same
analyte in two units, thresholds and free-text notes. Matching each
candidate name against this catalog (rather than a greedy regex) keeps
canonical labels and units and never records a note, a method or a
continuation line such as ``soit (IFCC)`` as a fake metric.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple


class Analyte(NamedTuple):
    """One recognized lab analyte and how to find its value."""

    key: str
    label: str
    unit: str
    find: str
    aliases: tuple[str, ...]


def _a(
    key: str,
    label: str,
    unit: str,
    aliases: tuple[str, ...],
    find: str | None = None,
) -> Analyte:
    """Build a catalog entry (``find`` defaults to the display unit)."""
    return Analyte(key, label, unit, unit if find is None else find, aliases)


ANALYTES: tuple[Analyte, ...] = (
    _a("hematies", "Hématies", "T/L", ("hematies",)),
    _a("hemoglobine", "Hémoglobine", "g/dL", ("hemoglobine",)),
    _a("hematocrite", "Hématocrite", "%", ("hematocrite",)),
    _a("vgm", "V.G.M.", "fL", ("v g m", "vgm", "volume globulaire moyen")),
    _a("tcmh", "T.C.M.H.", "pg", ("t c m h", "tcmh")),
    _a("ccmh", "C.C.M.H.", "g/dL", ("c c m h", "ccmh")),
    _a("idr", "I.D.R.", "%", ("i d r", "idr")),
    _a("leucocytes", "Leucocytes", "G/L", ("leucocytes",)),
    _a(
        "neutrophiles",
        "Polynucléaires neutrophiles",
        "G/L",
        ("polynucleaires neutrophiles", "neutrophiles"),
    ),
    _a(
        "eosinophiles",
        "Polynucléaires éosinophiles",
        "G/L",
        ("polynucleaires eosinophiles", "eosinophiles"),
    ),
    _a(
        "basophiles",
        "Polynucléaires basophiles",
        "G/L",
        ("polynucleaires basophiles", "basophiles"),
    ),
    _a("lymphocytes", "Lymphocytes", "G/L", ("lymphocytes",)),
    _a("monocytes", "Monocytes", "G/L", ("monocytes",)),
    _a("plaquettes", "Plaquettes", "G/L", ("plaquettes",)),
    _a("tp", "Taux de prothrombine", "%", ("taux de prothrombine",)),
    _a("inr", "INR", "", ("inr",)),
    _a("tq", "Temps de Quick", "s", ("temps de quick du patient",)),
    _a("tck", "TCK", "s", ("tck du patient",)),
    _a("sodium", "Sodium", "mmol/L", ("sodium",)),
    _a("potassium", "Potassium", "mmol/L", ("potassium",)),
    _a("chlore", "Chlore", "mmol/L", ("chlore", "chlorure")),
    _a("bicarbonates", "Bicarbonates", "mmol/L", ("bicarbonates",)),
    _a("creatinine", "Créatinine", "µmol/L", ("creatinine",)),
    _a(
        "dfg",
        "DFG (CKD-EPI)",
        "mL/min/1,73m²",
        ("estimation du dfg", "dfg"),
        find="mL/min/1,73m2",
    ),
    _a("uree", "Urée", "mmol/L", ("uree",)),
    _a("cpk", "CPK", "U/L", ("cpk", "creatine phospho kinase")),
    _a("crp", "CRP", "mg/L", ("crp", "proteine c reactive")),
    _a("pal", "Phosphatase alcaline", "U/L", ("phosphatase alcaline",)),
    _a("asat", "ASAT (TGO)", "U/L", ("asat", "transaminases tgo")),
    _a("alat", "ALAT (TGP)", "U/L", ("alat", "transaminases tgp")),
    _a("ggt", "GGT", "U/L", ("ggt", "gamma glutamyl")),
    _a("glycemie", "Glycémie à jeun", "g/L", ("glycemie a jeun", "glycemie")),
    _a(
        "hba1c",
        "Hémoglobine glyquée (HbA1c)",
        "%",
        ("hba1c", "hemoglobine glyquee"),
    ),
    _a(
        "cholesterol_total",
        "Cholestérol total",
        "g/L",
        ("cholesterol total", "cholesterol"),
    ),
    _a(
        "cholesterol_non_hdl",
        "Cholestérol non-HDL",
        "g/L",
        ("cholesterol non hdl",),
    ),
    _a(
        "cholesterol_hdl",
        "Cholestérol HDL",
        "g/L",
        ("cholesterol hdl", "hdl cholesterol"),
    ),
    _a(
        "cholesterol_ldl",
        "Cholestérol LDL",
        "g/L",
        ("cholesterol ldl", "ldl cholesterol"),
    ),
    _a("triglycerides", "Triglycérides", "g/L", ("triglycerides",)),
    _a("ferritine", "Ferritine", "µg/L", ("ferritine",)),
    _a("fer", "Fer sérique", "µmol/L", ("fer serique",)),
    _a("vitamine_b12", "Vitamine B12", "pg/mL", ("vitamine b12",)),
    _a("vitamine_b9", "Folates (Vit. B9)", "ng/mL", ("folates", "vitamine b9")),
    _a("vitamine_d", "Vitamine D", "ng/mL", ("vitamine d", "25 oh")),
    _a("tsh", "TSH", "mUI/L", ("tsh",)),
    _a("calcium", "Calcium", "mmol/L", ("calcium",)),
    _a("magnesium", "Magnésium", "mmol/L", ("magnesium",)),
    _a("acide_urique", "Acide urique", "µmol/L", ("acide urique",)),
    _a("proteines", "Protéines totales", "g/L", ("proteines totales",)),
    _a("albumine", "Albumine", "g/L", ("albumine",)),
    _a("iga", "Immunoglobulines A", "g/L", ("immunoglobulines a",)),
    _a("igg", "Immunoglobulines G", "g/L", ("immunoglobulines g",)),
    _a("igm", "Immunoglobulines M", "g/L", ("immunoglobulines m",)),
)


def normalize(text: str) -> str:
    """Lower-case, strip accents/dashes/punctuation, collapse whitespace."""
    unified = re.sub(r"[−–—/.]", " ", text)
    decomposed = unicodedata.normalize("NFKD", unified)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    without_flag = ascii_only.replace("[ac]", " ")
    cleaned = re.sub(r"[^a-z0-9]+", " ", without_flag)
    return re.sub(r"\s+", " ", cleaned).strip()


_INDEX: tuple[tuple[str, Analyte], ...] = tuple(
    sorted(
        (
            (normalize(alias), analyte)
            for analyte in ANALYTES
            for alias in analyte.aliases
        ),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)


def match(name: str) -> Analyte | None:
    """Return the analyte whose longest alias prefixes a candidate name."""
    norm = normalize(name)
    if not norm:
        return None
    for alias, analyte in _INDEX:
        if norm.startswith(alias):
            return analyte
    return None
