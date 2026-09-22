"""Prompts used to read a medical document (extraction, then summary).

Extraction (document model, e.g. MedGemma 1.5): only known metrics, each
with its unit, numbers and dates copied exactly — :mod:`document_grounding`
rejects anything the text does not prove. Long documents are read in
chunks so each answer stays short.

Summary (text model, e.g. MedGemma 27B): French summary, medications and
diagnoses, given the VERIFIED values so it never has to guess a number.
"""

from __future__ import annotations

from app.services import biology_catalog as bio
from app.services import metabolic_catalog as cat

_CHUNK = 5000
_MAX_CHUNKS = 8
_SUMMARY_CHARS = 12000

#: FibroScan metrics a document may carry: key → (label, unit).
LIVER = {
    cat.CAP_KEY: ("CAP FibroScan (graisse du foie)", "dB/m"),
    cat.LSM_KEY: ("Élasticité FibroScan (fibrose), E médiane", "kPa"),
}


def allowed() -> dict[str, tuple[str, str]]:
    """Every metric a document may fill: key → (label, unit)."""
    out = {bio.metric_key(a.key): (a.label, a.unit) for a in bio.ANALYTES}
    out.update(LIVER)
    return out


def chunks(text: str) -> list[str]:
    """The text cut on line boundaries into model-sized pieces."""
    out: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.splitlines():
        if current and size + len(line) > _CHUNK:
            out.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        out.append("\n".join(current))
    return out[:_MAX_CHUNKS]


_FORMAT = (
    'Answer ONLY with a JSON object: {"values": [{"key": ..., '
    '"value": number, "unit": ..., "date": "YYYY-MM-DD"}]}\n'
)
_RULES = (
    "Copy each number exactly as printed. Give each value the date it "
    "was measured (previous-results columns have their own dates; never "
    "use a birth date). Never guess or convert: if unsure, leave it out. "
    'If there is no such value, answer {"values": []}.\n\n'
)
_SCANNED = (
    "The pages are attached as images; the OCR text below may contain "
    "errors, prefer what you read on the images.\n"
)


def extraction(text: str, *, scanned: bool) -> str:
    """Prompt extracting measured values from one piece of a document."""
    keys = "\n".join(
        f"- {key}: {label} [{unit or 'sans unité'}]"
        for key, (label, unit) in allowed().items()
    )
    return (
        "You extract measured values from a French medical document "
        "(lab report, FibroScan…) for the patient's own health record.\n"
        f"{_SCANNED if scanned else ''}{_FORMAT}"
        f"Only these keys, with exactly this unit:\n{keys}\n{_RULES}"
        f"DOCUMENT:\n{text}"
    )


_SUMMARY_FORMAT = (
    'Réponds UNIQUEMENT en JSON : {"document_type": "biologie" | '
    '"fibroscan" | "imagerie" | "compte_rendu" | "ordonnance" | "autre", '
    '"summary": "2 à 4 phrases en français", "findings": ["constat"], '
    '"medications": [{"name": "médicament", "dose": "...", '
    '"frequency": "..."}], "conditions": ["diagnostic ou pathologie"]}\n'
)
_SUMMARY_RULES = (
    "Règles : écris en français ; n'utilise que ce qui est écrit dans le "
    "document ; les seuls chiffres permis sont les VALEURS VÉRIFIÉES "
    "ci-dessous ou recopiés exactement du document ; n'invente aucun "
    "stade, grade ni diagnostic ; listes vides si rien n'est mentionné.\n"
)


def summary(text: str, facts: list[str]) -> str:
    """Prompt summarising a document in French from verified values."""
    verified = "\n".join(f"- {fact}" for fact in facts) or "- (aucune)"
    return (
        "Tu es un assistant médical qui tient le dossier santé personnel "
        "du patient.\n"
        f"{_SUMMARY_FORMAT}{_SUMMARY_RULES}"
        f"VALEURS VÉRIFIÉES :\n{verified}\n\n"
        f"DOCUMENT :\n{text[:_SUMMARY_CHARS]}"
    )
