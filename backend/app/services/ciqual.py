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
    """References a meal may contain: foods named by a word of ``texts``.

    Only the head of a name (before its first comma) is matched; the
    foods whose name repeats other words of the text (« cuit »,
    « vapeur », « cru ») come first, then generic and plain ones — the
    list the model picks from.
    """
    said = {singular(w) for text in texts for w in tokens(text)} & _PREPARATION
    words: list[str] = []
    for text in texts:
        for word in tokens(text):
            base = singular(word)
            if len(base) >= _SHORTEST_FOOD_WORD and base not in _NOT_FOOD:
                words.append(base) if base not in words else None
    out: dict[str, Ref] = {}
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
