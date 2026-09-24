"""Tools: the user's usual foods — a sheet filled once from the label."""

from __future__ import annotations

import base64
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def list_foods() -> Any:
    """The user's foods, with their label values per 100 g.

    Each: name, brand, aliases, package weight (g), values per 100 g,
    note, photo ids and kinds. A meal that names one (or lists it in
    log_meal ``foods``) is computed from its label, not estimated.
    """
    return await client.get("/foods")


@mcp.tool()
async def save_food(
    name: str,
    per_100g: dict[str, float] | None = None,
    package_g: float | None = None,
    brand: str = "",
    aliases: str = "",
    note: str = "",
    food_id: str | None = None,
    unit_name: str = "",
    unit_g: float | None = None,
    source: str = "",
    barcode: str = "",
) -> Any:
    """Add a food (or replace ``food_id``'s sheet).

    ``per_100g``: energy_kcal, protein_g, carbs_g, sugars_g, fat_g,
    sat_fat_g, fiber_g, sodium_mg (1 g of salt = 400 mg of sodium).
    ``aliases``: other names used in meals, comma separated.
    ``unit_name`` / ``unit_g``: how it is counted (« tomate », 120):
    « 2 tomates » in a meal is then 240 g. ``source``: where the values
    come from (« étiquette », « Ciqual 2025 · 20385 · … »).
    """
    body = {
        "name": name,
        "brand": brand,
        "aliases": aliases,
        "package_g": package_g,
        "unit_name": unit_name,
        "unit_g": unit_g,
        "per_100g": per_100g or {},
        "note": note,
        "source": source,
        "barcode": barcode,
    }
    if food_id:
        return await client.request("PUT", f"/foods/{food_id}", body=body)
    return await client.post("/foods", body)


@mcp.tool()
async def search_ciqual(query: str, limit: int = 20) -> Any:
    """Search the ANSES Ciqual 2025 table (offline, ~3,500 foods).

    Every word of ``query`` must appear (« saumon vapeur »); generic
    foods first. Each: code, name, group, per_100g — e.g. to fill
    save_food with reference values.
    """
    return await client.get("/ciqual", {"q": query, "limit": limit})


@mcp.tool()
async def lookup_barcode(barcode: str) -> Any:
    """A packaged food by barcode on Open Food Facts (if the hub allows).

    Needs FOOD_LOOKUP_ONLINE=true on the hub; only the barcode is sent.
    A proposal to check, then save_food.
    """
    return await client.get(f"/openfoodfacts/{barcode}")


@mcp.tool()
async def delete_food(food_id: str) -> Any:
    """Delete a food and its photos (meals keep their reading)."""
    return await client.request("DELETE", f"/foods/{food_id}")


@mcp.tool()
async def read_food_label(photo_base64: str) -> Any:
    """Read a pack or its nutrition table with the vision model.

    A proposal, nothing saved: name, brand, package_g, per_100g. Check
    it, then save_food.
    """
    raw = base64.b64decode(photo_base64)
    files = {"file": ("etiquette.jpg", raw, "image/jpeg")}
    return await client.upload("/foods/read-label", files, {})


@mcp.tool()
async def add_food_photo(
    food_id: str, photo_base64: str, kind: str = "pack"
) -> Any:
    """Attach a photo to a food: ``kind`` pack (the box) or label."""
    raw = base64.b64decode(photo_base64)
    files = {"file": ("photo.jpg", raw, "image/jpeg")}
    return await client.upload(
        f"/foods/{food_id}/photos", files, {"kind": kind}
    )
