"""AI clinical synthesis of the whole record (text model, grounded).

The text model (e.g. MedGemma 27B, the stronger medical reasoner) writes
a French synthesis for the doctor from the numbered facts of
:mod:`clinical_facts` only; :mod:`synthesis_check` drops every sentence
without a fact reference or with a number its facts do not contain.
"""

from __future__ import annotations

from typing import Any

from app.core import ollama
from app.models.base import utcnow
from app.services import synthesis_check
from app.services.clinical_facts import Fact, as_json

_TOKENS = 1500
_FACTS_CHARS = 14000  # keeps prompt + answer within the model context
#: (answer key, title, a fact reference is required)
SECTIONS = (
    ("synthese", "Synthèse", True),
    ("evolutions", "Évolutions", True),
    ("points_attention", "Points d'attention", True),
    ("a_discuter", "À discuter avec le médecin", True),
    ("donnees_manquantes", "Données manquantes", False),
)
_RULES = """Tu es médecin interniste. Rédige en français une synthèse clinique \
du dossier ci-dessous pour le médecin traitant.
RÈGLES STRICTES :
1. Utilise UNIQUEMENT les faits numérotés ci-dessous ; n'invente rien.
2. Termine chaque phrase par les faits utilisés entre crochets, ex. [F3][F12].
3. Tout chiffre écrit doit figurer tel quel dans les faits cités.
4. Aucun diagnostic absent des faits ; tu peux relever une cohérence ou une \
discordance entre faits (ex. poids en baisse et HbA1c en baisse).
5. Aucune prescription ni posologie : formule les pistes « à discuter avec le \
médecin ».
6. Signale dans donnees_manquantes les examens utiles absents ou anciens.
Réponds uniquement en JSON :
{"synthese": ["3 à 6 phrases"], "evolutions": ["..."], \
"points_attention": ["..."], "a_discuter": ["..."], \
"donnees_manquantes": ["..."]}
FAITS DU DOSSIER :
"""


async def synthesize(facts: list[Fact]) -> dict[str, Any]:
    """The checked synthesis (or the error) with the facts it could use."""
    out: dict[str, Any] = {
        "model": ollama.text_model(),
        "generated_at": utcnow().isoformat(),
        "facts": as_json(facts),
        "sections": [],
        "rejected": 0,
        "rejected_items": [],
        "error": None,
    }
    if not facts:
        out["error"] = "dossier vide : aucune donnée à synthétiser"
        return out
    try:
        answer = await ollama.text_json(prompt(facts), max_tokens=_TOKENS)
    except Exception as exc:  # noqa: BLE001 - shown in the report
        out["error"] = str(exc)[:300] or type(exc).__name__
        return out
    _fill(out, answer, {f.id: f.text for f in facts})
    return out


def prompt(facts: list[Fact]) -> str:
    """Rules, answer format and the numbered facts (size-capped)."""
    lines: list[str] = []
    size = 0
    for fact in facts:
        text = f"[{fact.id}] {fact.section} — {fact.text}"
        size += len(text) + 1
        if size > _FACTS_CHARS:
            break
        lines.append(text)
    return _RULES + "\n".join(lines)


def _fill(
    out: dict[str, Any], answer: dict[str, Any], facts: dict[str, str]
) -> None:
    """Check every sentence of every section; count the rejected."""
    for key, title, cite in SECTIONS:
        kept = []
        for sentence in synthesis_check.items(answer.get(key)):
            item, reason = synthesis_check.check(sentence, facts, cite=cite)
            if item is not None:
                kept.append(item)
            else:
                out["rejected_items"].append(
                    {"text": sentence[:300], "reason": reason}
                )
        out["sections"].append({"key": key, "title": title, "items": kept})
    out["rejected"] = len(out["rejected_items"])
