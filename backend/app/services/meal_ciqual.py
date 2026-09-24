"""A meal's foods valued from the Ciqual table, not from the model.

The model is given, for the words of the description and of the photo,
a short list of Ciqual references (code : name) and answers, for each
food, the code of the closest one (same food, same cooking). The code
then replaces the model's nutrient estimates with the table's values
for its grams: the same food and quantity always give the same numbers.
A food without a valid code keeps the model's estimate (checked). Only
this module sets ``source`` / ``reference``: what the model writes
there is dropped.
"""

from __future__ import annotations

from typing import Any

from app.services import ciqual

SOURCE = "Ciqual"
_MAX_GRAMS = 1500.0


def refs(texts: list[str]) -> list[dict[str, str]]:
    """The references offered to the model for these texts."""
    return [{"code": r.code, "name": r.name} for r in ciqual.candidates(texts)]


def fill(items: Any, offered: set[str]) -> Any:
    """The model's items; those naming an offered code valued from the table.

    A code outside the list the model was given is ignored (the model
    may invent one that exists but names another food).
    """
    if not isinstance(items, list):
        return items
    return [
        _filled(raw, offered) if isinstance(raw, dict) else raw for raw in items
    ]


def _filled(raw: dict[str, Any], offered: set[str]) -> dict[str, Any]:
    """One item: the table's values for its grams, or the model's."""
    item = {k: v for k, v in raw.items() if k not in ("source", "reference")}
    code = str(item.pop("ciqual", None) or "").strip()
    ref = ciqual.get(code) if code in offered else None
    grams = _grams(item.get("grams"))
    if ref is None or grams is None:
        return item
    return {
        **item,
        "grams": grams,
        **ciqual.portion(ref, grams),
        "ciqual": ref.code,
        "source": SOURCE,
        "reference": f"{ciqual.VERSION} · {ref.name}",
    }


def _grams(value: Any) -> float | None:
    """A plausible quantity in grams, or None."""
    try:
        grams = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return grams if 0 < grams <= _MAX_GRAMS else None
