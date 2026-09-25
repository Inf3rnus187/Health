"""The model's remarks on a meal, checked against what the code computed.

* A doubt on values that are known (« vérifier l'étiquette réelle ») is
  cut when the meal holds foods of « Mes aliments ».
* Every quantity a remark quotes (« 24,6 g », « 562,4 mg ») must be one
  the code computed for what the remark talks about: the values of the
  foods it names (their line, their sheet per 100 g), or the meal's
  totals when it names none or speaks of the meal (« total », « repas »),
  at the rounding written (sodium also as grams of sodium or of salt).
  Otherwise the brackets holding it are cut, or the remark is dropped:
  « grâce au saumon (24,6 g) » — the meal's protein; the salmon has
  20,5 g — loses its brackets.
* A remark too long ends at its last full sentence, never mid-word.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.text_norm import singular, tokens

#: Per food (the words of its name, its numbers), and the meal's numbers.
Known = tuple[list[tuple[set[str], set[float]]], set[float]]

_DOUBT = re.compile(
    r"\s*[(\[,;—–-]*\s*(?:à |il faut |pensez à |penser à )?v[ée]rifi\w*"
    r"[^.;()]*(?:étiquette|composition|valeurs?|emballage|teneur)"
    r"[^.;()]*[)\]]?",
    re.IGNORECASE,
)
_QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:mg|g|kcal|µg)\b", re.IGNORECASE)
_ASIDE = re.compile(r"\s*\([^()]*\)")
_MEAL_WORDS = frozenset("total totale repas ensemble".split())
_SALT_PER_NA = 400.0  # 1 g of salt = 400 mg of sodium
_SHORTEST = 12
_LONGEST = 300
_NAME_WORD = 3


def numbers(
    items: list[dict[str, Any]],
    totals: dict[str, float],
    foods: list[dict[str, Any]],
) -> Known:
    """What each food and the whole meal may be quoted with."""
    sheets = {str(f.get("id")): f for f in foods}
    per_food = []
    for item in items:
        values = _values(item)
        sheet = sheets.get(str(item.get("food_id")))
        if sheet:
            values |= _values(sheet.get("per_100g") or {})
        name = str(item.get("name") or "").split(" · ")[0]
        per_food.append((_words(name), values))
    return per_food, _values(totals)


def clean(texts: list[str], trusted: bool, known: Known | None) -> list[str]:
    """The remarks without doubts on known values nor unchecked numbers."""
    out = []
    for text in texts:
        kept = _DOUBT.sub("", text).strip(" ,;—–-") if trusted else text
        if known is not None:
            kept = _checked(kept, _allowed(kept, known))
        if len(kept.strip()) >= _SHORTEST:
            out.append(kept.strip())
    return out


def _checked(text: str, allowed: set[float]) -> str:
    """Brackets quoting an unchecked number cut; the remark, if it does."""
    kept = _ASIDE.sub(lambda m: m[0] if _true(m[0], allowed) else "", text)
    return kept if _true(kept, allowed) else ""


def short(text: Any) -> str:
    """One line, at most 300 characters, ending at a full sentence."""
    line = " ".join(str(text).split())
    if len(line) <= _LONGEST:
        return line
    cut = line[:_LONGEST]
    end = max(cut.rfind(". "), cut.rfind("; "), cut.rfind("! "))
    if end >= _SHORTEST * 2:
        return cut[: end + 1]
    return cut[: cut.rfind(" ")].rstrip(" ,;:") + "…"


def _allowed(text: str, known: Known) -> set[float]:
    """The numbers of the foods the remark names, and the meal's."""
    per_food, meal = known
    said = {singular(w) for w in tokens(text)}
    named = [values for words, values in per_food if words & said]
    allowed = {100.0}.union(*named)
    if not named or said & _MEAL_WORDS:
        allowed |= meal
    return allowed


def _true(text: str, allowed: set[float]) -> bool:
    """Each « 557 mg » in ``text`` is an allowed number, as rounded there."""
    for match in _QTY.finditer(text):
        raw = match[1].replace(",", ".")
        digits = len(raw.split(".")[1]) if "." in raw else 0
        if not any(round(k, digits) == float(raw) for k in allowed):
            return False
    return True


def _values(found: dict[str, Any]) -> set[float]:
    """The numbers of a line, a sheet per 100 g or the totals."""
    out: set[float] = set()
    for key, value in found.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        out.add(float(value))
        if key == "sodium_mg":  # also as grams of sodium or of salt
            out |= {value / 1000, value / _SALT_PER_NA}
    return out


def _words(name: str) -> set[str]:
    """The words naming a food in a remark (« saumon », « aubergine »)."""
    return {singular(w) for w in tokens(name) if len(w) > _NAME_WORD}
