"""The two model calls that read a document: values, then summary.

* values — the document model (vision-capable, e.g. MedGemma 1.5) reads
  each chunk (a scanned document: its page images + OCR text);
* summary — the text model (e.g. MedGemma 27B, the stronger medical
  reasoner) writes the French summary, lists medications and diagnoses,
  given the verified values. Names it returns must appear in the text.

Each call's answer length is capped; a failure is reported, not raised.
"""

from __future__ import annotations

from typing import Any

from app.core import ollama
from app.services import document_prompt
from app.services.document_text import DocContent
from app.services.textfold import fold as _fold

_VALUES_TOKENS = 1024
_SUMMARY_TOKENS = 900
_TEXT_MAX = 300


async def extract_values(content: DocContent) -> tuple[list[Any], str | None]:
    """Every value proposed by the document model, or an error."""
    if not content.text.strip() and not content.images:
        return [], "document illisible (ni texte ni image)"
    pieces = (
        [content.text]
        if content.scanned
        else document_prompt.chunks(content.text)
    )
    values: list[Any] = []
    try:
        for piece in pieces:
            answer = await ollama.generate_json(
                document_prompt.extraction(piece, scanned=content.scanned),
                ollama.document_model(),
                images=content.images,
                max_tokens=_VALUES_TOKENS,
            )
            found = answer.get("values")
            values.extend(found if isinstance(found, list) else [])
    except Exception as exc:  # noqa: BLE001 - exact values still count
        return values, str(exc)[:300]
    return values, None


async def summarize(
    text: str, facts: list[str]
) -> tuple[dict[str, Any], str | None]:
    """French summary, findings, medications, diagnoses (text model)."""
    if not text.strip():
        return {}, None
    try:
        answer = await ollama.text_json(
            document_prompt.summary(text, facts), max_tokens=_SUMMARY_TOKENS
        )
    except Exception as exc:  # noqa: BLE001 - the values are already kept
        return {}, str(exc)[:300]
    return _clean(answer, text), None


def _clean(answer: dict[str, Any], text: str) -> dict[str, Any]:
    """Keep well-formed fields; drop names the document never mentions."""
    folded = _fold(text)
    meds = [
        _med(m)
        for m in _list(answer.get("medications"))
        if isinstance(m, dict) and _fold(str(m.get("name", ""))) in folded
    ]
    return {
        "document_type": str(answer.get("document_type") or "")[:20] or None,
        "summary": str(answer.get("summary") or "")[:600] or None,
        "findings": [str(f)[:_TEXT_MAX] for f in _list(answer.get("findings"))],
        "medications": [m for m in meds if m["name"]],
        "conditions": [
            str(c)[:120]
            for c in _list(answer.get("conditions"))
            if _fold(str(c)) and _fold(str(c)) in folded
        ],
    }


def _med(item: dict[str, Any]) -> dict[str, str]:
    """A medication line (name, dose, frequency)."""
    return {
        "name": str(item.get("name") or "").strip()[:120],
        "dose": str(item.get("dose") or "").strip()[:60],
        "frequency": str(item.get("frequency") or "").strip()[:80],
    }


def _list(value: Any) -> list[Any]:
    """A JSON list, or empty."""
    return value[:20] if isinstance(value, list) else []
