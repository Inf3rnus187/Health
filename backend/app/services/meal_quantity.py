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
"""

from __future__ import annotations

from typing import Any

from app.services.food_match import COUNTS, GRAMS, PACKS, parts, span

_FILLERS = frozenset("de d du des la le l en a au".split())
_BEFORE, _AFTER = 8, 3  # « un quart de la grosse boîte d'aubergines »


def grams_in(food: Any, text: str) -> float | None:
    """The grams of ``food`` the description gives, or None."""
    for words in parts(text):
        at = span(food, words)
        if at is None:
            continue
        start, end = at
        found = _grams(words[end : end + _AFTER]) or _grams_before(
            words[max(0, start - _BEFORE) : start]
        )
        if found is not None:
            return found
        return _counted(food, words[max(0, start - _BEFORE) : start])
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


def _counted(food: Any, before: list[str]) -> float | None:
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
        return (food.portion_g or food.package_g) if pack else None
    unit = food.package_g if pack or not food.unit_g else food.unit_g
    return round(count * unit, 1) if unit else None


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
