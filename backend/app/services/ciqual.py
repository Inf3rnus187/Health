"""The ANSES Ciqual table: reference values per 100 g of ~3,500 foods.

« Anses. 2025. Table de composition nutritionnelle des aliments
Ciqual » (Licence Ouverte / Etalab 2.0), extracted by
``tools/ciqual_extract.py`` into ``app/data/ciqual.tsv`` and shipped
with the hub: read offline, nothing is sent anywhere, the same for every
user. ANSES notation: ``-`` unknown (None), ``traces`` (0), ``< x``
(below the detection limit: x / 2).

A meal's foods are valued from here when the model names their Ciqual
reference: the same food always gets the same values.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from app.services.text_norm import singular, tokens

VERSION = "Ciqual 2025"
NUTRIENTS = (
    "energy_kcal", "protein_g", "carbs_g", "sugars_g", "fat_g",
    "sat_fat_g", "fiber_g", "sodium_mg",
)  # fmt: skip
_PATH = Path(__file__).resolve().parents[1] / "data" / "ciqual.tsv"
_SHORTEST_FOOD_WORD = 4
#: Words of a description that never name a food.
_NOT_FOOD = frozenset(
    "avec sans nature cuit cuite cuits cuites cru crue crus crues sauce "
    "aucune aucun matiere grasse grasses entree plat dessert tranche "
    "tranches demi moitie morceau morceaux portion portions sachet boite "
    "pave paves gramme grammes petit petite gros grosse fait maison huile "
    "beurre deux trois quatre cinq sept huit neuf".split()
)
#: How a food is prepared: the words that tell two references apart.
_PREPARATION = frozenset(
    "cru crue cuit cuite vapeur grille grillee poele poelee roti rotie four "
    "bouilli bouillie frit frite fume fumee rissole rissolee saute sautee "
    "micro sec seche entier entiere ecreme complet nature peau".split()
)
#: « cuit » in a description: any of these ways of cooking.
_COOKED = frozenset(
    "cuit cuite grille grillee poele poelee roti rotie four bouilli bouillie "
    "vapeur frit frite saute sautee braise braisee".split()
)
_RAW = frozenset("cru crue".split())
#: References less likely to be what a plain description means.
_SPECIAL = frozenset("bio label preleve preemballe marine".split())
_PARTS = re.compile(r"[,;:+\n]|\bet\b|\bavec\b|\bpuis\b", re.IGNORECASE)
_PER_PHRASE = 6


class Ref(NamedTuple):
    """One food of the table."""

    code: str
    name: str
    group: str
    per_100g: dict[str, float | None]


@lru_cache(maxsize=1)
def table() -> dict[str, Ref]:
    """Every food of the table, by code."""
    with _PATH.open(encoding="utf-8", newline="") as source:
        rows = csv.DictReader(source, delimiter="\t")
        refs = [_ref(row) for row in rows]
    return {ref.code: ref for ref in refs}


def get(code: str) -> Ref | None:
    """One food by its Ciqual code (None when unknown)."""
    return table().get(code.strip())


def search(query: str, limit: int = 20) -> list[Ref]:
    """The foods whose name has every word asked, generic ones first."""
    asked = [singular(w) for w in tokens(query) if len(w) > 1]
    if not asked:
        return []
    found = [r for r in table().values() if _has_all(r.name, asked)]
    return sorted(found, key=lambda r: _rank(r, asked[0]))[:limit]


def candidates(
    texts: list[str], per_word: int = 8, most: int = 60
) -> list[Ref]:
    """References a meal may contain — the list the model picks from.

    First, for each part of a text (« un filet de poulet cuit »), the
    references naming all its food words (filet and poulet), cooked
    ones first when it says « cuit » (grillé, poêlé, rôti…), raw when
    « cru », then generic before « bio », « label rouge », « mariné »,
    « préemballé ». Then, word by word, the foods whose head (before the
    first comma) has the word, those repeating the text's preparation
    words first, generic and plain ones next.
    """
    said = {singular(w) for text in texts for w in tokens(text)} & _PREPARATION
    words: list[str] = []
    for text in texts:
        words += [w for w in _food_words(text) if w not in words]
    out: dict[str, Ref] = {ref.code: ref for ref in _by_phrase(texts)}
    for word in words:
        heads = [r for r in table().values() if word in _head(r.name)]
        ranked = sorted(heads, key=lambda r: _pick(r, word, said))
        for ref in ranked[:per_word]:
            out.setdefault(ref.code, ref)
    return list(out.values())[:most]


def portion(ref: Ref, grams: float) -> dict[str, float]:
    """The nutrients of ``grams`` of the food (energy from the table).

    An unknown value counts 0; unknown energy is computed from the
    macros (4 kcal/g protein and carbohydrates, 9 fat, 2 fibre).
    """
    ratio = grams / 100
    values = {
        k: round((ref.per_100g.get(k) or 0.0) * ratio, 1)
        for k in NUTRIENTS
        if k != "energy_kcal"
    }
    energy = ref.per_100g.get("energy_kcal")
    if energy is None:
        energy = 4 * ((ref.per_100g.get("protein_g") or 0) + (
            ref.per_100g.get("carbs_g") or 0)) + 9 * (
            ref.per_100g.get("fat_g") or 0) + 2 * (
            ref.per_100g.get("fiber_g") or 0)  # fmt: skip
    return {"energy_kcal": round(energy * ratio, 1), **values}


def _ref(row: dict[str, str]) -> Ref:
    """A table line."""
    values = {k: _value(row[k]) for k in NUTRIENTS}
    return Ref(row["code"], row["name"], row["group"], values)


def _value(text: str) -> float | None:
    """« 12,5 » → 12.5, « traces » → 0, « < 0,5 » → 0.25, « - » → None."""
    plain = text.strip().replace(",", ".")
    if not plain or plain == "-":
        return None
    if plain == "traces":
        return 0.0
    if plain.startswith("<"):
        return round(float(plain[1:].strip()) / 2, 4)
    return float(plain)


def _food_words(text: str) -> list[str]:
    """The words of ``text`` that may name a food (singular, in order)."""
    out: list[str] = []
    for word in tokens(text):
        base = singular(word)
        long = len(base) >= _SHORTEST_FOOD_WORD
        if long and base not in _NOT_FOOD and base not in out:
            out.append(base)
    return out


def _by_phrase(texts: list[str]) -> list[Ref]:
    """References naming every food word of a part (« filet de poulet »)."""
    found: list[Ref] = []
    for text in texts:
        for part in _PARTS.split(text):
            words = _food_words(part)
            if len(words) < 2:  # noqa: PLR2004 - one word: the word lists
                continue
            said = {singular(w) for w in tokens(part)} & _PREPARATION
            hits = [r for r in table().values() if _has_all(r.name, words)]
            ranked = sorted(hits, key=lambda r: _cooking(r, said))
            found += ranked[:_PER_PHRASE]
    return found


def _cooking(ref: Ref, said: set[str]) -> tuple[int, int, int, int]:
    """Cooked as said, generic, not special, short: first."""
    name = {singular(w) for w in tokens(ref.name)}
    if said & _COOKED:
        cooking = 0 if name & _COOKED else (2 if name & _RAW else 1)
    elif said & _RAW:
        cooking = 0 if name & _RAW else 1
    else:
        cooking = 0
    generic = _rank(ref, "")[1]
    return (cooking, int(bool(name & _SPECIAL)), generic, len(ref.name))


def _head(name: str) -> set[str]:
    """The words before the first comma, singular (« Tomate ronde »)."""
    return {singular(w) for w in tokens(name.split(",")[0])}


def _has_all(name: str, asked: list[str]) -> bool:
    """Whether every asked word starts a word of the name."""
    words = [singular(w) for w in tokens(name)]
    return all(any(w.startswith(a) for w in words) for a in asked)


def _pick(ref: Ref, word: str, said: set[str]) -> tuple[int, ...]:
    """Named by the word first, then prepared as said, generic, short."""
    starts, generic, size = _rank(ref, word)
    echo = len({singular(w) for w in tokens(ref.name)} & said)
    return (starts, -echo, generic, size)


def _rank(ref: Ref, first: str) -> tuple[int, int, int]:
    """Generic, starting with the word, short: first."""
    name = ref.name.lower()
    generic = "aliment moyen" in name or "sans précision" in name
    starts = singular(tokens(name)[0]) == first if tokens(name) else False
    return (0 if starts else 1, 0 if generic else 1, len(name))
