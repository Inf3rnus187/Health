"""MCP tools: the stock of « Mes aliments », and what to cook from it."""

from __future__ import annotations

from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def food_stock() -> Any:
    """What is left of each food with a stock (for « what do I cook? »).

    Per food: ``name`` (name · brand · package), ``grams`` left,
    ``packs`` / ``units`` / ``portions`` (packages, units, usual
    portions ``portion_g`` it makes), ``missing`` (meals ate more than
    was entered: suggest a count), ``last_purchase``. To suggest a meal:
    only foods in stock, grams within what is left (the usual portion
    first), mind the user's conditions (medical_record), and say what
    will remain; log it afterwards with log_meal.
    """
    return await client.get("/stock")


@mcp.tool()
async def add_stock(
    food: str | None = None,
    food_id: str | None = None,
    barcode: str | None = None,
    kind: str = "purchase",
    packs: float | None = None,
    units: float | None = None,
    grams: float | None = None,
    at: str | None = None,
    note: str = "",
) -> Any:
    """Enter a purchase (« j'ai acheté 3 boîtes de … »), a loss or a count.

    The food by ``food`` (its name; a word's start is enough), ``food_id``
    or ``barcode``; two sizes answering one name are refused (ask which,
    or use the barcode / id from list_foods). The quantity: ``packs``
    (× the package), ``units`` (× the unit: 6 tomates) or ``grams``; a
    purchase with none is one pack. ``kind``: purchase, out (thrown,
    given — not eaten: meals are deducted by themselves) or count (what
    is left now: « il m'en reste une boîte »). ``at``: ISO time when not
    now. A new product: save_food first (one sheet per size).
    """
    body = {
        "food": food,
        "food_id": food_id,
        "barcode": barcode,
        "kind": kind,
        "packs": packs,
        "units": units,
        "grams": grams,
        "at": at,
        "note": note,
    }
    return await client.post(
        "/stock", {k: v for k, v in body.items() if v is not None}
    )


@mcp.tool()
async def stock_history(food_id: str) -> Any:
    """A food's stock moves (newest first) and the meals that ate it."""
    return await client.get(f"/stock/{food_id}/moves")


@mcp.tool()
async def delete_stock_move(move_id: str) -> Any:
    """Delete a stock move entered by mistake (ask first)."""
    return await client.request("DELETE", f"/stock/moves/{move_id}")
