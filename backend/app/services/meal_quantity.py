"""How much of a catalogue food a meal's description says was eaten.

Read by code, never guessed, so the same words always give the same
grams. Within the part of the description naming the food
(:mod:`food_match`: « un pavé de saumon » names « Saumon sauvage rose »):

* grams written next to it: « saumon 100g », « saumon cuit nature
  100g » (« cuit », « nature », « cru »… skipped), « 150 g de riz »
  (kg too);
* else a count before it: « 2 tomates », « un demi concombre », « une
  tranche de comté », « ½ sachet de riz » — times the food's unit
  (``unit_g``), or its package (``package_g``) for « sachet », « boîte »,
  « pot »… or when it has no unit; a pack without a count is the
  food's usual portion (``portion_g``: the small box, ¼ of the big
  one), else one pack (« petite boîte d'aubergines » = the box);
* else nothing (None): the form's grams, the photo or the package decide.

``read`` also says how (« écrit », « compté », « portion », « paquet »)
for the analysis to show. ``written`` applies the description to the
model's other lines too: grams written (« tomates 240 g ») are kept as
they are; a count (« 2 tomates », « un demi concombre », « une tranche
de comté ») is read by the code and multiplied by the weight of ONE
unit the model gives (``unit_g``) — never the share a photo shows.
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
_MOST_UNIT_G = 1500.0


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
        found = _grams(_after(words, end)) or _grams_before(
            words[max(0, start - _BEFORE) : start]
        )
        if found is not None:
            return found, "écrit"
        return _counted(food, words[max(0, start - _BEFORE) : start])
    return None, ""


def written(items: Any, text: str) -> Any:
    """The model's lines, with the quantities the description gives.

    Only for lines that are not a food of « Mes aliments » (those are
    read with their sheet). Each line says where its grams come from:
    « écrit » (grams in the description), « unités » (a count in the
    description × the model's weight of one unit, shown as « 2 × 120
    g ») or « IA » (the model's estimate).
    """
    if not isinstance(items, list):
        return items
    return [_said(raw, text) if isinstance(raw, dict) else raw for raw in items]


def _said(raw: dict[str, Any], text: str) -> dict[str, Any]:
    """One line of the model, with what the description says of it."""
    item = {k: v for k, v in raw.items() if k not in ("grams_from", "units")}
    item["grams_from"] = "IA"
    name = "" if item.get("food_id") else str(item.get("name") or "")
    grams = _written(name, text) if name else None
    if grams is not None:
        item["grams"], item["grams_from"] = grams, "écrit"
        return item
    count, unit = _said_count(name, text), _unit(item.get("unit_g"))
    if name and count and unit:
        item["grams"] = round(count * unit, 1)
        item["grams_from"] = "unités"
        item["units"] = f"{count:g} × {unit:g} g".replace(".", ",")
    return item


def _said_count(name: str, text: str) -> float | None:
    """« 2 tomates », « un demi concombre »: the count before the food."""
    own = {singular(w) for w in tokens(name) if len(w) > 2} - _VAGUE  # noqa: PLR2004
    for words in parts(text):
        at = [i for i, w in enumerate(words) if w in own]
        if at:
            return _count(words[max(0, at[0] - _BEFORE) : at[0]])[0]
    return None


def _unit(value: Any) -> float | None:
    """The model's weight of one unit, when plausible."""
    try:
        grams = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return grams if 0 < grams <= _MOST_UNIT_G else None


def _written(name: str, text: str) -> float | None:
    """Grams written next to a word of ``name`` (« tomates 240 g »)."""
    own = {singular(w) for w in tokens(name) if len(w) > 2} - _VAGUE  # noqa: PLR2004
    for words in parts(text):
        at = [i for i, w in enumerate(words) if w in own]
        if not at:
            continue
        found = _grams(_after(words, at[-1] + 1)) or (
            _grams_before(words[max(0, at[0] - _BEFORE) : at[0]])
        )
        if found is not None:
            return found
    return None


def _after(words: list[str], start: int) -> list[str]:
    """The words right after a food, « cuit », « nature »… skipped."""
    return [w for w in words[start:] if w not in _VAGUE][:_AFTER]


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
    count, pack = _count(before)
    if count is None:
        return _pack(food) if pack else (None, "")
    unit = food.package_g if pack or not food.unit_g else food.unit_g
    return (round(count * unit, 1), "compté") if unit else (None, "")


def _count(before: list[str]) -> tuple[float | None, bool]:
    """The count said before a food (« un demi » = ½), and if a pack."""
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
    return count, pack


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
