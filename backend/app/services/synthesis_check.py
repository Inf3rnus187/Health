"""Keep only the synthesis sentences the record proves.

A sentence must cite at least one known fact (``[F12]``) and every number
it writes must appear in the facts it cites (the same value, or that
value rounded). Anything else is dropped and reported with its reason.
"""

from __future__ import annotations

import re
from typing import Any

_GROUP = re.compile(r"\[([^\]]*)\]")
_REF = re.compile(r"F\s*(\d+)")
#: A value: digits not glued to a letter (the 1 of HbA1c is not one).
_NUMBER = re.compile(r"(?<![^\W\d_])\d+(?:[.,]\d+)?")
#: A code with digits (HbA1c, S3, F0-F1, B12): written as in the facts.
_CODE = re.compile(r"[^\W\d_]+\d[\w-]*")
_SPACE = re.compile(r"\s+([.,])")
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=\S)")


def items(value: Any) -> list[str]:
    """The model's answer for a section as a list of sentences."""
    if isinstance(value, str):
        return [s for s in _SENTENCE.split(value.strip()) if s]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()][:12]
    return []


def check(
    sentence: str, facts: dict[str, str], *, cite: bool = True
) -> tuple[dict[str, Any] | None, str | None]:
    """The sentence with its references, or the reason it is rejected."""
    refs = [f"F{n}" for g in _GROUP.findall(sentence) for n in _REF.findall(g)]
    text = _SPACE.sub(r"\1", " ".join(_GROUP.sub("", sentence).split()))
    unknown = [ref for ref in refs if ref not in facts]
    if unknown:
        return None, f"référence inconnue {unknown[0]}"
    if cite and not refs:
        return None, "aucun fait cité"
    source = " ".join(facts[ref] for ref in refs)
    missing = _unproven(text, source) or (
        _uncoded(text, source) if refs else None
    )
    if missing:
        return None, f"chiffre absent des faits cités : {missing}"
    return {"text": text, "facts": list(dict.fromkeys(refs))}, None


def _unproven(text: str, source: str) -> str | None:
    """The first number of ``text`` that ``source`` does not contain."""
    known = [_value(n) for n in _NUMBER.findall(source)]
    for raw in map(str, _NUMBER.findall(text)):
        wanted = _value(raw)
        places = len(raw.replace(",", ".").partition(".")[2])
        if not any(round(k, places) == wanted for k in known):
            return raw
    return None


def _uncoded(text: str, source: str) -> str | None:
    """The first code of ``text`` (e.g. S2) that ``source`` lacks."""
    known = source.casefold()
    for code in map(str, _CODE.findall(text)):
        if code.casefold() not in known:
            return code
    return None


def _value(raw: str) -> float:
    """A written number as a float (French decimal comma)."""
    return float(raw.replace(",", "."))
