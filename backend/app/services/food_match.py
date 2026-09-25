"""Which food of « Mes aliments » a meal's description names.

The description is cut into parts (commas, « et », « + », « avec »…).
A part names a food when:

* it holds its whole name (« poulet basquaise ») or one of its aliases
  (« riz micro-ondes »), as before; or
* it holds a word of its name (« saumon ») and nothing that is not the
  food's (other words of its name, its brand, its unit « pavé »), a
  count, a size (« petite »), a pack (« boîte ») or a neutral word
  (« nature », « cuit ») — *and* something confirms it: a pack, its
  unit, its brand, or two words of its name.

So « un pavé de saumon » names « Saumon sauvage rose » (1 pavé = 100 g)
and « petite boîte d'aubergines » names « Aubergines cuisinées à la
provençale »; « filet de poulet » does not name « Poulet basquaise »
(« filet » is not its word), nor « 2 pommes » « Pommes rissolées »
(nothing confirms). A part two foods fit equally names neither: the
Ciqual table or the model decides.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.text_norm import singular, tokens

COUNTS = {
    "un": 1.0, "une": 1.0, "deux": 2.0, "trois": 3.0, "quatre": 4.0,
    "cinq": 5.0, "six": 6.0, "demi": 0.5, "demie": 0.5, "moitie": 0.5,
    "quart": 0.25,
}  # fmt: skip
PACKS = frozenset(
    "sachet boite paquet pot barquette conserve bocal brique canette "
    "bouteille".split()
)
GRAMS = {"g": 1.0, "gr": 1.0, "gramme": 1.0, "kg": 1000.0, "kilo": 1000.0}
_NEUTRAL = frozenset(
    "de d du des la le l les en a au aux mon ma mes unite petit petite "
    "grand grande gros grosse moyen moyenne mini entier entiere entree "
    "plat dessert nature cuit cuite chaud chaude froid froide rechauffe "
    "rechauffee four micro onde grille grillee poele vapeur roti rotie "
    "braise mijote".split()
)
_SPLIT = re.compile(r"[,;+\n]|\bet\b|\bpuis\b|\bavec\b", re.IGNORECASE)
_SHORT = 2  # « à », « la »: not words of a name
Span = tuple[int, int]


def parts(text: str) -> list[list[str]]:
    """The description's parts, as singular plain words."""
    return [[singular(w) for w in tokens(p)] for p in _SPLIT.split(text or "")]


def span(food: Any, words: list[str]) -> Span | None:
    """Where one part's ``words`` name ``food`` (see above), or None."""
    found = _whole(food, words)
    return found[1] if found else _partial(food, words)


def named(foods: list[Any], text: str) -> list[Any]:
    """The foods the description names, each once, in the order said."""
    out: list[Any] = []
    for words in parts(text):
        ranked = sorted(
            ((_rank(f, words), i) for i, f in enumerate(foods)), reverse=True
        )
        best = ranked[0] if ranked and ranked[0][0] > (0, 0) else None
        if best is None or (len(ranked) > 1 and ranked[1][0] == best[0]):
            continue
        food = foods[best[1]]
        if all(food.id != f.id for f in out):
            out.append(food)
    return out


def fits(food: Any, name: str) -> bool:
    """Whether a food the model lists (« Pavé de saumon ») is ``food``."""
    words = [singular(w) for w in tokens(name)]
    if _whole(food, words):
        return True
    own = _words(food.name)
    return any(w in own for w in words) and all(
        _allowed(food, w) for w in words
    )


def _rank(food: Any, words: list[str]) -> tuple[int, int]:
    """How well a part names a food: whole > partial, then words matched."""
    whole = _whole(food, words)
    if whole:
        return 2, whole[0]
    found = _partial(food, words)
    own = _words(food.name)
    return (1, len({w for w in words if w in own})) if found else (0, 0)


def _whole(food: Any, words: list[str]) -> tuple[int, Span] | None:
    """An alias said whole, else every word of the name (with its size)."""
    for alias in str(food.aliases or "").split(","):
        phrase = [singular(w) for w in tokens(alias)]
        size = len(phrase)
        for i in range(len(words) - size + 1) if size else ():
            if words[i : i + size] == phrase:
                return size, (i, i + size)
    name = _words(food.name)
    if name and all(w in words for w in name):
        at = [words.index(w) for w in name]
        return len(name), (min(at), max(at) + 1)
    return None


def _partial(food: Any, words: list[str]) -> Span | None:
    """A word of the name, nothing foreign, and a confirmation."""
    own = _words(food.name)
    hits = [i for i, w in enumerate(words) if w in own]
    if not hits or not all(_allowed(food, w) for w in words):
        return None
    marks = PACKS | _words(food.brand) | _words(food.unit_name)
    sure = len({words[i] for i in hits}) > 1 or any(w in marks for w in words)
    return (hits[0], hits[-1] + 1) if sure else None


def _allowed(food: Any, word: str) -> bool:
    """A word that may stand next to the food's name in a part."""
    if word[0].isdigit() or word in COUNTS or word in GRAMS:
        return True
    if word in PACKS or word in _NEUTRAL:
        return True
    return word in _words(food.name) | _words(food.brand) | _words(
        food.unit_name
    )


def _words(text: str | None) -> set[str]:
    """The significant words of a name, brand or unit."""
    return {singular(w) for w in tokens(text or "") if len(w) > _SHORT}
