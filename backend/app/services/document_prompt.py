"""The prompt a document model receives to read a medical document.

The model may only report values for known metrics (the lab catalog and
the FibroScan measures), each with its unit, and must copy numbers and
dates exactly as printed: :mod:`document_grounding` then rejects any
value the document text does not prove.
"""

from __future__ import annotations

from app.services import biology_catalog as bio
from app.services import metabolic_catalog as cat
from app.services.document_text import DocContent

_MAX_CHARS = 12000

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


_FORMAT = (
    "Answer ONLY with a JSON object:\n"
    '{"document_type": one of "biologie", "fibroscan", "imagerie", '
    '"compte_rendu", "ordonnance", "autre", '
    '"document_date": "YYYY-MM-DD" or null, '
    '"summary": "2-3 short sentences in French: what the document is '
    'and its key findings", '
    '"values": [{"key": ..., "value": number, "unit": ..., '
    '"date": "YYYY-MM-DD"}]}\n'
)
_RULES = (
    "Copy each number exactly as printed. Give each value the date it "
    "was measured (previous-results columns have their own dates). "
    "Never guess or convert: if unsure, leave the value out.\n\n"
)
_SCANNED = (
    "The pages are attached as images; the OCR text below may contain "
    "errors, prefer what you read on the images.\n"
)


def build(content: DocContent) -> str:
    """The extraction prompt for one document."""
    keys = "\n".join(
        f"- {key}: {label} [{unit or 'sans unité'}]"
        for key, (label, unit) in allowed().items()
    )
    return (
        "You read French medical documents (lab reports, FibroScan, "
        "letters, imaging reports) for the patient's own health record.\n"
        f"{_SCANNED if content.scanned else ''}{_FORMAT}"
        f"Rules for values: only these keys, with exactly this unit:\n"
        f"{keys}\n{_RULES}DOCUMENT:\n{content.text[:_MAX_CHARS]}"
    )
