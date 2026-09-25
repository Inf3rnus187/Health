"""The model's remarks on a meal, checked against what the code knows.

* A doubt on values that are known (« vérifier l'étiquette réelle ») is
  cut when the meal holds foods of « Mes aliments ».
* Every quantity a remark quotes (« 24,6 g », « 562,4 mg ») must be one
  the code computed for what the remark talks about: the values of the
  foods it names (their line, their sheet per 100 g), or the meal's
  totals when it names none or speaks of the meal (« total », « repas »),
  at the rounding written (sodium also in grams, and as salt in g or mg).
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
* « sel » and « sodium » name what they quote: « sel (120,9 mg) » where
  120,9 mg is the sodium becomes « sodium (120,9 mg) », « 1,4 g de
  sodium » where 1,4 g is the salt becomes « 1,4 g de sel ». The word is
  the one right after the quantity (« de sel »), else the last one before
  it in its sentence; a word two quantities disagree on is left alone.
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
    #: Its sodium and its salt as (unit, value), to tell one from the other.
    sodium: frozenset[tuple[str, float]] = frozenset()
    salt: frozenset[tuple[str, float]] = frozenset()


#: The meal's foods, and the whole meal (its totals).
Known = tuple[list[Said], Said]

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
#: A quantity that may be of sodium or salt, and the words for each.
_NA_QTY = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|g)\b", re.IGNORECASE)
_NA_WORD = re.compile(r"\b(sel|sodium)\b", re.IGNORECASE)
_NA_AFTER = re.compile(r"\s*(?:de\s+|d['’]\s*)(sel|sodium)\b", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.;!?](?=\s|$)")
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
    sodium, salt = _salts(totals)
    meal = Said(
        words=frozenset(),
        values=frozenset(_values(totals)),
        percents=frozenset(),
        nova=None,
        ingredients="",
        sodium=frozenset(sodium),
        salt=frozenset(salt),
    )
    return said, meal


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
    scope = named + ([known[1]] if not named or words & _MEAL_WORDS else [])
    text = _salt(text, scope)
    quantities = {100.0}.union(*(food.values for food in scope))
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


def _salt(text: str, scope: list[Said]) -> str:
    """« sel » quoting sodium becomes « sodium », and the other way."""
    sodium = set().union(*(food.sodium for food in scope))
    salt = set().union(*(food.salt for food in scope))
    fixes: dict[tuple[int, int], set[str]] = {}
    for match in _NA_QTY.finditer(text):
        word, kind = _owner(text, match), _kind(match, sodium, salt)
        if word is not None and kind:
            fixes.setdefault(word.span(1), set()).add(kind)
    for (start, end), kinds in sorted(fixes.items(), reverse=True):
        said = text[start:end]
        if len(kinds) == 1 and (kind := kinds.pop()) != said.lower():
            new = kind.capitalize() if said[:1].isupper() else kind
            text = text[:start] + new + text[end:]
    return text


def _owner(text: str, quantity: re.Match[str]) -> re.Match[str] | None:
    """The « sel » or « sodium » a quantity is of.

    The one right after it (« 302 mg de sel »), else the last one before
    it in its sentence.
    """
    after = _NA_AFTER.match(text, quantity.end())
    if after:
        return after
    ends = [m.end() for m in _SENTENCE_END.finditer(text, 0, quantity.start())]
    start = ends[-1] if ends else 0
    before = list(_NA_WORD.finditer(text, start, quantity.start()))
    return before[-1] if before else None


def _kind(
    quantity: re.Match[str],
    sodium: set[tuple[str, float]],
    salt: set[tuple[str, float]],
) -> str:
    """« sodium » or « sel » when the quantity is one and not the other."""
    unit = quantity[2].lower()
    is_sodium = _known(quantity[1], {v for u, v in sodium if u == unit})
    is_salt = _known(quantity[1], {v for u, v in salt if u == unit})
    if is_sodium == is_salt:
        return ""
    return "sodium" if is_sodium else "sel"


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
    sodium, salt = _salts(item)
    per_100g = _salts((sheet or {}).get("per_100g") or {})
    return Said(
        words=frozenset(_words(name)),
        values=frozenset(values),
        percents=frozenset(percents),
        nova=nova if isinstance(nova, int) else None,
        ingredients=ingredients if len(ingredients) < _WHOLE else "",
        sodium=frozenset(sodium | per_100g[0]),
        salt=frozenset(salt | per_100g[1]),
    )


def _values(found: dict[str, Any]) -> set[float]:
    """The numbers of a line, a sheet per 100 g or the totals."""
    out: set[float] = set()
    for value in found.values():
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        out.add(float(value))
    sodium, salt = _salts(found)  # also in g, and as salt in g or mg
    return out | {value for _, value in sodium | salt}


def _salts(
    found: dict[str, Any],
) -> tuple[set[tuple[str, float]], set[tuple[str, float]]]:
    """Its sodium (mg, g) and its salt (g, mg), as (unit, value)."""
    mg = found.get("sodium_mg")
    if isinstance(mg, bool) or not isinstance(mg, int | float):
        return set(), set()
    salt_g = mg / _SALT_PER_NA
    return {("mg", mg), ("g", mg / 1000)}, {
        ("g", salt_g),
        ("mg", salt_g * 1000),
    }


def _words(name: str) -> set[str]:
    """The words naming a food in a remark (« saumon », « aubergine »)."""
    return {singular(w) for w in tokens(name) if len(w) > _NAME_WORD}
