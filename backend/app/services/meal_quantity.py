"""How much of a catalogue food a meal's description says was eaten.

Read by code, never guessed, so the same words always give the same
grams. Within the part of the description naming the food
(:mod:`food_match`: « un pavé de saumon » names « Saumon sauvage rose »):

* grams written next to it: « saumon 100g », « 150 g de riz » (kg too);
* else a count before it: « 2 tomates », « un demi concombre », « une
  tranche de comté », « ½ sachet de riz » — times the food's unit
  (``unit_g``), or its package (``package_g``) for « sachet », « boîte »,
  « pot »… or when it has no unit; a pack without a count is the
  food's usual portion (``portion_g``: the small box, ¼ of the big
  one), else one pack (« petite boîte d'aubergines » = the box);
* else nothing (None): the form's grams, the photo or the package decide.

``read`` also says how (« écrit », « compté », « portion », « paquet »)
for the analysis to show. ``written`` applies grams written in the
description to the model's other lines too (« tomates 240 g »): what
was weighed is never replaced by an estimate.
"""

from __future__ import annotations

from typing import Any

from app.services.food_match import COUNTS, GRAMS, PACKS, parts, span
from app.services.text_norm import singular, tokens

_FILLERS = frozenset("de d du des la le l en a au".split())
#: Words of a food's name that do not say which food it is.
_VAGUE = frozenset(
    "cru crue cuit cuite nature frais fraiche sans precision aliment "
    "moyen".split()
)
_BEFORE, _AFTER = 8, 3  # « un quart de la grosse boîte d'aubergines »


def grams_in(food: Any, text: str) -> float | None:
    """The grams of ``food`` the description gives, or None."""
    return read(food, text)[0]


def read(food: Any, text: str) -> tuple[float | None, str]:
    """The grams of ``food`` the description gives, and how it gives them."""
    for words in parts(text):
        at = span(food, words)
        if at is None:
            continue
        start, end = at
        found = _grams(words[end : end + _AFTER]) or _grams_before(
            words[max(0, start - _BEFORE) : start]
        )
        if found is not None:
            return found, "écrit"
        return _counted(food, words[max(0, start - _BEFORE) : start])
    return None, ""


def written(items: Any, text: str) -> Any:
    """The model's lines, with the grams the description writes for them.

    Only for lines that are not a food of « Mes aliments » (those are
    read with their sheet). Each line says where its grams come from:
    « écrit » (the description) or « IA » (the model's estimate).
    """
    if not isinstance(items, list):
        return items
    out: list[Any] = []
    for raw in items:
        if not isinstance(raw, dict):
            out.append(raw)
            continue
        item = {k: v for k, v in raw.items() if k != "grams_from"}
        own = None if item.get("food_id") else str(item.get("name") or "")
        grams = _written(own, text) if own else None
        if grams is not None:
            item["grams"] = grams
        item["grams_from"] = "écrit" if grams is not None else "IA"
        out.append(item)
    return out


def _written(name: str, text: str) -> float | None:
    """Grams written next to a word of ``name`` (« tomates 240 g »)."""
    own = {singular(w) for w in tokens(name) if len(w) > 2} - _VAGUE  # noqa: PLR2004
    for words in parts(text):
        at = [i for i, w in enumerate(words) if w in own]
        if not at:
            continue
        found = _grams(words[at[-1] + 1 : at[-1] + 1 + _AFTER]) or (
            _grams_before(words[max(0, at[0] - _BEFORE) : at[0]])
        )
        if found is not None:
            return found
    return None


def _grams(after: list[str]) -> float | None:
    """« 100 g » right after the food."""
    for i, word in enumerate(after[:-1]):
        unit = GRAMS.get(after[i + 1])
        if _number(word) is not None and unit:
            return float(_number(word) or 0) * unit
    return None


def _grams_before(before: list[str]) -> float | None:
    """« 150 g de riz »: grams just before the food."""
    rest = [w for w in before if w not in _FILLERS]
    if len(rest) >= 2 and rest[-1] in GRAMS and _number(rest[-2]) is not None:  # noqa: PLR2004
        return float(_number(rest[-2]) or 0) * GRAMS[rest[-1]]
    return None


def _counted(food: Any, before: list[str]) -> tuple[float | None, str]:
    """A count before the food, times its unit or its package."""
    count, pack = None, False
    for word in reversed([w for w in before if w not in _FILLERS]):
        if word in PACKS:
            pack = True
            continue
        value = _number(word)
        if value is None:
            if count is not None:
                break
            continue
        count = value if count is None else _combine(value, count)
    if count is None:
        return _pack(food) if pack else (None, "")
    unit = food.package_g if pack or not food.unit_g else food.unit_g
    return (round(count * unit, 1), "compté") if unit else (None, "")


def _pack(food: Any) -> tuple[float | None, str]:
    """« petite boîte » without a count: the usual portion, else the box."""
    if food.portion_g:
        return float(food.portion_g), "portion"
    return (float(food.package_g), "paquet") if food.package_g else (None, "")


def _combine(earlier: float, later: float) -> float:
    """« un demi » is ½, « deux demi » 1: a count before a fraction."""
    return earlier * later if later < 1 else later


def _number(word: str) -> float | None:
    """« 2 », « 1,5 », « deux », « demi » → a number."""
    if word in COUNTS:
        return COUNTS[word]
    try:
        return float(word.replace(",", "."))
    except ValueError:
        return None
