"""The AI's remarks agree with the reference table of the meal.

The code places each nutrient against its meal's part of the day
(:mod:`meal_reference`: below, within, above). The model is given these
verdicts and told to follow them; what it writes is then checked: a
remark that calls a nutrient low, moderate or high against its verdict
(« apport modéré en protéines » for proteins above a dinner's part) is
replaced by the code's own sentence (« Protéines 36 g : au-dessus de la
part d'un dîner (17,5–20 g) »). A remark that names several nutrients
or no clear level in one clause is left as it is.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.textfold import fold

#: key → (name in a sentence, pattern of the folded text).
_NUTRIENTS: dict[str, tuple[str, str]] = {
    "sat_fat_g": ("acides gras saturés", r"satur"),
    "sugars_g": ("sucres", r"\bsucres?\b"),
    "carbs_g": ("glucides", r"\bglucides?\b"),
    "fat_g": ("lipides", r"\b(?:lipides?|graisses?|matieres? grasses?)\b"),
    "protein_g": ("protéines", r"\bproteine|\bproteique"),
    "fiber_g": ("fibres", r"\bfibres?\b"),
    "sodium_mg": ("sodium", r"\b(?:sodium|sel|salee?s?)\b"),
    "energy_kcal": ("énergie", r"\b(?:energie|energetique|calori|kcal)"),
}
#: The level a clause gives (folded text); the first alternative found at
#: a place wins: « trop peu » is low, « pas trop » moderate, « trop » high.
_LEVELS = re.compile(
    r"(?P<below>\b(?:trop peu|pas assez|peu (?:de|d'|eleve|important|riche)"
    r"|faibles?|pauvres?|bas(?:se)?s?|insuffisante?s?|manque|carence"
    r"|legere?s?|modeste)\b)"
    r"|(?P<within>\b(?:pas (?:tres |trop )?(?:elevee?s?|importante?s?|riches?"
    r"|excessi(?:f|ve)s?)|pas trop|sans exces|moderee?s?|raisonnables?"
    r"|mesuree?s?|correcte?s?|equilibree?s?|adaptee?s?|convenables?"
    r"|suffisante?s?|adequate?s?|dans (?:la norme|les reperes|la part))\b)"
    r"|(?P<above>\b(?:elevee?s?|riches?|importante?s?(?! de)|beaucoup"
    r"|exces(?:si(?:f|ve)s?)?|trop|abondante?s?|fortes?|genereu(?:x|se)s?"
    r"|copieu(?:x|se)s?|au-dessus|depasse\w*|non negligeable)\b)"
)
_CLAUSES = re.compile(r"[.;:,!?()]| mais | alors que | tandis que | et ")
_SAID = {
    "below": "en dessous de",
    "within": "dans",
    "above": "au-dessus de",
}
_OF = {
    "breakfast": "d'un petit-déjeuner",
    "lunch": "d'un déjeuner",
    "dinner": "d'un dîner",
}


def prompt_lines(reference: dict[str, Any] | None) -> str:
    """The verdicts as the model reads them (nothing for a snack)."""
    rows = _rows(reference)
    if not rows:
        return ""
    lines = [
        "Repères officiels de ce type de repas, calculés par le logiciel "
        "(ils font foi : tes remarques les suivent, « au-dessus » se dit "
        "élevé, « dans la part » modéré, « en dessous » faible ; ne les "
        "contredis jamais) :"
    ]
    lines += [f"- {sentence(key, row, reference)}" for key, row in rows]
    return "\n".join(lines) + "\n"


def align(
    judged: dict[str, Any], reference: dict[str, Any] | None
) -> dict[str, Any]:
    """The judgement with each remark agreeing with the verdicts."""
    if not _rows(reference):
        return judged
    out = dict(judged)
    for part in ("positives", "watch"):
        out[part] = _agreeing(judged.get(part) or [], reference)
    verdict = judged.get("verdict")
    if isinstance(verdict, str) and _wrong(verdict, reference):
        kept = [c for c in verdict.split(", ") if not _wrong(c, reference)]
        out["verdict"] = _sentence(", ".join(kept)) if kept else None
    return out


def sentence(key: str, row: dict[str, Any], reference: Any) -> str:
    """« Protéines 36 g : au-dessus de la part d'un dîner (17,5–20 g). »."""
    name = _NUTRIENTS[key][0]
    of = _OF.get(str(reference.get("meal_type")), "du repas")
    value = _n(row["value"])
    band = f"{_n(row['low'])}–{_n(row['high'])} {row['unit']}"
    said = _SAID[row["verdict"]]
    return (
        f"{name.capitalize()} {value} {row['unit']} : {said} la part {of} "
        f"({band})."
    )


def _agreeing(texts: list[str], reference: Any) -> list[str]:
    """Each remark, or the code's sentence where it contradicts it."""
    out: list[str] = []
    for text in texts:
        wrong = _wrong(text, reference)
        row = reference["rows"].get(wrong)
        line = sentence(wrong, row, reference) if wrong else text
        if line not in out:
            out.append(line)
    return out


def _wrong(text: str, reference: Any) -> str | None:
    """The nutrient a clause of ``text`` says the opposite of, if any."""
    rows = reference["rows"]
    for clause in _CLAUSES.split(fold(text)):
        keys = [k for k, (_, p) in _NUTRIENTS.items() if re.search(p, clause)]
        keys = [k for k in keys if not (k == "fat_g" and "sat_fat_g" in keys)]
        levels = {m.lastgroup for m in _LEVELS.finditer(clause)}
        if len(keys) != 1 or len(levels) != 1 or keys[0] not in rows:
            continue
        verdict = rows[keys[0]].get("verdict")
        if verdict and levels != {verdict}:
            return keys[0]
    return None


def _rows(reference: dict[str, Any] | None) -> list[tuple[str, Any]]:
    """The rows that carry a verdict (a meal type with a part)."""
    rows = (reference or {}).get("rows") or {}
    return [(k, r) for k, r in rows.items() if r.get("verdict")]


def _sentence(text: str) -> str:
    """Capitalised, ending with a full stop."""
    text = text.strip()
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


def _n(value: float) -> str:
    """One decimal at most, with a comma: 17.5 → « 17,5 »."""
    return f"{round(float(value), 1):g}".replace(".", ",")
