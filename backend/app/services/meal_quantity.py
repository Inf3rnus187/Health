"""How much of a catalogue food a meal's description says was eaten.

Read by code, never guessed, so the same words always give the same
grams. Within the part of the description naming the food (parts are
separated by commas, « et », « + »…):

* grams written next to it: « saumon 100g », « 150 g de riz » (kg too);
* else a count before it: « 2 tomates », « un demi concombre », « une
  tranche de comté », « ½ sachet de riz » — times the food's unit
  (``unit_g``), or its package (``package_g``) for « sachet », « boîte »,
  « pot »… or when it has no unit;
* else nothing (None): the form's grams, the photo or the package decide.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.text_norm import singular, tokens

_WORDS = {
    "un": 1.0, "une": 1.0, "deux": 2.0, "trois": 3.0, "quatre": 4.0,
    "cinq": 5.0, "six": 6.0, "demi": 0.5, "demie": 0.5, "moitie": 0.5,
    "quart": 0.25,
}  # fmt: skip
_PACKS = frozenset(
    "sachet boite paquet pot barquette conserve bocal brique canette "
    "bouteille".split()
)
_FILLERS = frozenset("de d du des la le l en a au".split())
_GRAMS = {"g": 1.0, "gr": 1.0, "gramme": 1.0, "kg": 1000.0, "kilo": 1000.0}
_SPLIT = re.compile(r"[,;+\n]|\bet\b|\bpuis\b|\bavec\b", re.IGNORECASE)
_BEFORE, _AFTER = 5, 3


def grams_in(food: Any, text: str) -> float | None:
    """The grams of ``food`` the description gives, or None."""
    for part in _SPLIT.split(text or ""):
        words = [singular(w) for w in tokens(part)]
        at = _position(food, words)
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


def _position(food: Any, words: list[str]) -> tuple[int, int] | None:
    """Where the food is named in ``words`` (its alias, else its name)."""
    for alias in str(food.aliases or "").split(","):
        phrase = [singular(w) for w in tokens(alias)]
        found = _find(phrase, words)
        if found is not None:
            return found
    name = [singular(w) for w in tokens(food.name) if len(w) > 2]  # noqa: PLR2004
    if name and all(w in words for w in name):
        first = min(words.index(w) for w in name)
        return first, max(words.index(w) for w in name) + 1
    return None


def _find(phrase: list[str], words: list[str]) -> tuple[int, int] | None:
    """Where ``phrase`` appears whole in ``words``."""
    size = len(phrase)
    for i in range(len(words) - size + 1) if size else ():
        if words[i : i + size] == phrase:
            return i, i + size
    return None


def _grams(after: list[str]) -> float | None:
    """« 100 g » right after the food."""
    for i, word in enumerate(after[:-1]):
        unit = _GRAMS.get(after[i + 1])
        if _number(word) is not None and unit:
            return float(_number(word) or 0) * unit
    return None


def _grams_before(before: list[str]) -> float | None:
    """« 150 g de riz »: grams just before the food."""
    rest = [w for w in before if w not in _FILLERS]
    if len(rest) >= 2 and rest[-1] in _GRAMS and _number(rest[-2]) is not None:  # noqa: PLR2004
        return float(_number(rest[-2]) or 0) * _GRAMS[rest[-1]]
    return None


def _counted(food: Any, before: list[str]) -> float | None:
    """A count before the food, times its unit or its package."""
    count, pack = None, False
    for word in reversed([w for w in before if w not in _FILLERS]):
        if word in _PACKS:
            pack = True
            continue
        value = _number(word)
        if value is None:
            if count is not None:
                break
            continue
        count = value if count is None else _combine(value, count)
    if count is None:
        return None
    unit = food.package_g if pack or not food.unit_g else food.unit_g
    return round(count * unit, 1) if unit else None


def _combine(earlier: float, later: float) -> float:
    """« un demi » is ½, « deux demi » 1: a count before a fraction."""
    return earlier * later if later < 1 else later


def _number(word: str) -> float | None:
    """« 2 », « 1,5 », « deux », « demi » → a number."""
    if word in _WORDS:
        return _WORDS[word]
    try:
        return float(word.replace(",", "."))
    except ValueError:
        return None
