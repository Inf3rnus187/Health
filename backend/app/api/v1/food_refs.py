"""Reference values: the Ciqual table, Open Food Facts, daily intakes.

Ciqual (ANSES, shipped with the hub, offline) holds generic foods —
« Tomate, crue », « Saumon, cuit à la vapeur »; Open Food Facts (only
when ``FOOD_LOOKUP_ONLINE=true``) packaged products by barcode. Both are
proposals for a food sheet: nothing is saved here. The official daily
references (EU, ANSES, WHO) are what each meal is set against.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query

from app.core.deps import Principal, ReaderDep, require_scope
from app.core.errors import NotFoundError
from app.core.scopes import WRITE_MEASUREMENTS
from app.services import ciqual, food_off, meal_reference

router = APIRouter(tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.get("/ciqual")
async def search(
    principal: ReaderDep,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, Any]:
    """Foods of the Ciqual table whose name has every word of ``q``.

    Generic foods first (« aliment moyen »). Each: ``code``, ``name``,
    ``group``, ``per_100g`` (energy_kcal … sodium_mg; null = unknown).
    """
    del principal
    found = ciqual.search(q, limit)
    return {"version": ciqual.VERSION, "items": [_out(r) for r in found]}


@router.get("/ciqual/{code}")
async def detail(
    principal: ReaderDep, code: Annotated[str, Path(pattern=r"^\d{1,8}$")]
) -> dict[str, Any]:
    """One food of the Ciqual table."""
    del principal
    ref = ciqual.get(code)
    if ref is None:
        raise NotFoundError("Unknown Ciqual code")
    return {"version": ciqual.VERSION, **_out(ref)}


@router.get("/openfoodfacts/{barcode}")
async def barcode(
    principal: WriteDep, barcode: Annotated[str, Path(max_length=14)]
) -> dict[str, Any]:
    """A packaged food by its barcode, from Open Food Facts.

    Needs ``FOOD_LOOKUP_ONLINE=true`` (only the barcode is sent). A
    proposal to check against the pack: ``name``, ``brand``,
    ``package_g``, ``per_100g`` (plausible values only), ``barcode``,
    ``source``.
    """
    del principal
    return await food_off.lookup(barcode)


@router.get("/nutrition/references")
async def references(principal: ReaderDep) -> dict[str, Any]:
    """The official daily references each meal is set against.

    ``daily``: energy_kcal … sodium_mg with ``value`` (a day, adult-type),
    ``unit``, ``kind`` (``limit`` not to exceed, ``target`` to reach,
    ``reference`` a benchmark) and ``source``; ``share_pct``: the
    indicative part of the day of a breakfast, lunch or dinner (none for
    a snack); ``sources``: name and link of each. A meal's own figures
    are in its ``reference`` (``GET /meals/{id}``).
    """
    del principal
    return meal_reference.table()


def _out(ref: ciqual.Ref) -> dict[str, Any]:
    """A table food for the page."""
    return {
        "code": ref.code,
        "name": ref.name,
        "group": ref.group,
        "per_100g": ref.per_100g,
    }
