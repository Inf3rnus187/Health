"""The model's remarks on a meal, checked against what the code knows.

* A doubt on values that are known (« vérifier l'étiquette réelle ») is
  cut when the meal holds foods of « Mes aliments ».
* Every quantity a remark quotes (« 24,6 g », « 562,4 mg ») must be one
  the code computed for what the remark talks about: the values of the
  foods it names (their line, their sheet per 100 g), or the meal's
  totals when it names none or speaks of the meal (« total », « repas »),
  at the rounding written (sodium also as grams of sodium or of salt).
  A percentage (« 1,4 % ») must be in the named foods' ingredients or
  their share of fruits and vegetables. Otherwise the brackets holding
  it are cut, or the remark is dropped: « grâce au saumon (24,6 g) » —
  the meal's protein; the salmon has 20,5 g — loses its brackets.
* « ultra-transformé » said of foods whose NOVA group is known and
  below 4 becomes « transformé » (NOVA 3) or « peu transformé » (1, 2);
  « ne sont pas transformées » said of NOVA 3 or 4 becomes « sont
  transformées » (« ultra-transformées » for 4). « pas ultra-transformé »,
  true of NOVA 3, stays.
* « sucre ajouté » said of foods whose whole ingredients are known and
  hold no sugar drops the remark.
* A remark too long ends at its last full sentence, never mid-word.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.text_norm import norm, singular, tokens


@dataclass(frozen=True)
class Said:
    """What one food of the meal may be quoted with."""

    words: frozenset[str]
    values: frozenset[float]
    percents: frozenset[float]
    nova: int | None
    #: Its ingredients, when known whole ("" otherwise).
    ingredients: str


#: The meal's foods, and the numbers of the whole meal.
Known = tuple[list[Said], frozenset[float]]

_DOUBT = re.compile(
    r"\s*[(\[,;—–-]*\s*(?:à |il faut |pensez à |penser à )?v[ée]rifi\w*"
    r"[^.;()]*(?:étiquette|composition|valeurs?|emballage|teneur)"
    r"[^.;()]*[)\]]?",
    re.IGNORECASE,
)
_QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:mg|g|kcal|µg)\b", re.IGNORECASE)
_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_ASIDE = re.compile(r"\s*\([^()]*\)")
#: « ultra-transformé », but not « pas / non ultra-transformé » (true of 3).
_ULTRA = re.compile(
    r"(?<!pas )(?<!non )(?<!non-)ultra[- ]?transform[ée](e?s?)", re.IGNORECASE
)
#: « ne sont pas transformées », « non transformé »: false of NOVA 3, 4.
_NOT = re.compile(
    r"\bn(?:e\s+|')(sont|est)\s+pas\s+transform[ée](e?s?)"
    r"|\bnon[- ]transform[ée](e?s?)",
    re.IGNORECASE,
)
_ADDED_SUGAR = re.compile(r"sucres? ajout|ajouts? de sucre", re.IGNORECASE)
_SUGARS = ("sucre", "sirop", "glucose", "fructose", "dextrose", "saccharose")
_MEAL_WORDS = frozenset("total totale repas ensemble".split())
_SALT_PER_NA = 400.0  # 1 g of salt = 400 mg of sodium
_WHOLE = 400  # ingredients the model was given; longer: cut, not known
_SHORTEST = 12
_LONGEST = 300
_NAME_WORD = 3
_ULTRA_NOVA = 4
_PROCESSED_NOVA = 3


def numbers(
    items: list[dict[str, Any]],
    totals: dict[str, float],
    foods: list[dict[str, Any]],
) -> Known:
    """What each food and the whole meal may be quoted with."""
    sheets = {str(f.get("id")): f for f in foods}
    said = [_said(item, sheets.get(str(item.get("food_id")))) for item in items]
    return said, frozenset(_values(totals))


def clean(texts: list[str], trusted: bool, known: Known | None) -> list[str]:
    """The remarks without doubts, wrong numbers or wrong claims."""
    out = []
    for text in texts:
        kept = _DOUBT.sub("", text).strip(" ,;—–-") if trusted else text
        if known is not None:
            kept = _checked(kept, known)
        if len(kept.strip()) >= _SHORTEST:
            out.append(kept.strip())
    return out


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


def _checked(text: str, known: Known) -> str:
    """One remark checked against the foods it names and the meal."""
    words = {singular(w) for w in tokens(text)}
    named = [food for food in known[0] if food.words & words]
    about = named or known[0]
    if _ADDED_SUGAR.search(text) and _no_sugar(about):
        return ""
    text = _nova(text, about)
    quantities = {100.0}.union(*(food.values for food in named))
    if not named or words & _MEAL_WORDS:
        quantities |= known[1]
    percents = set().union(*(food.percents for food in about))
    kept = _ASIDE.sub(
        lambda m: m[0] if _true(m[0], quantities, percents) else "", text
    )
    return kept if _true(kept, quantities, percents) else ""


def _true(text: str, quantities: set[float], percents: set[float]) -> bool:
    """Each quantity and percentage quoted is an allowed one."""
    return all(
        _known(match[1], allowed)
        for pattern, allowed in ((_QTY, quantities), (_PCT, percents))
        for match in pattern.finditer(text)
    )


def _known(raw: str, allowed: set[float]) -> bool:
    """« 562,4 » is one of ``allowed``, rounded as written."""
    value = raw.replace(",", ".")
    digits = len(value.split(".")[1]) if "." in value else 0
    return any(round(k, digits) == float(value) for k in allowed)


def _nova(text: str, foods: list[Said]) -> str:
    """What the remark says of processing, made true to the NOVA group."""
    groups = [f.nova for f in foods if f.nova is not None]
    if not groups:
        return text
    top = max(groups)
    if top < _PROCESSED_NOVA:
        return _ULTRA.sub(lambda m: "peu transformé" + m[1], text)
    word = "ultra-transformé" if top >= _ULTRA_NOVA else "transformé"
    if top == _PROCESSED_NOVA:
        text = _ULTRA.sub(lambda m: word + m[1], text)
    return _NOT.sub(lambda m: _said_so(m, word), text)


def _said_so(match: re.Match[str], word: str) -> str:
    """« ne sont pas transformées » → « sont transformées »."""
    if match[1]:
        return f"{match[1]} {word}{match[2]}"
    return f"{word}{match[3]}"


def _no_sugar(foods: list[Said]) -> bool:
    """Whether the foods' ingredients are known whole and hold no sugar."""
    known = [f.ingredients for f in foods if f.ingredients]
    return (
        bool(known)
        and len(known) == len(foods)
        and not any(s in norm(i) for i in known for s in _SUGARS)
    )


def _said(item: dict[str, Any], sheet: dict[str, Any] | None) -> Said:
    """What a line may be quoted with (and its sheet's details)."""
    values = _values(item) | _values((sheet or {}).get("per_100g") or {})
    about = (sheet or {}).get("open_food_facts") or {}
    ingredients = str(about.get("ingredients") or "")
    percents = {
        float(n.replace(",", ".")) for n in _NUMBER.findall(ingredients)
    }
    if isinstance(about.get("fruits_veg_pct"), int | float):
        percents.add(float(about["fruits_veg_pct"]))
    nova = about.get("nova")
    name = str(item.get("name") or "").split(" · ")[0]
    return Said(
        words=frozenset(_words(name)),
        values=frozenset(values),
        percents=frozenset(percents),
        nova=nova if isinstance(nova, int) else None,
        ingredients=ingredients if len(ingredients) < _WHOLE else "",
    )


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
