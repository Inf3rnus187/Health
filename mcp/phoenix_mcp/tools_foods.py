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
    portion_g: float | None = None,
    product_info: dict[str, Any] | None = None,
) -> Any:
    """Add a food (or replace ``food_id``'s sheet: send every field).

    One sheet per size: the small box (185 g) and the big one are two
    sheets with their own ``package_g`` (and barcode); a meal saying
    « petite boîte » / « grosse boîte » takes the right one.
    ``portion_g``: what the user usually eats of it (the whole small
    box, ¼ of the big one), counted when a meal gives no quantity.
    ``product_info``: pass lookup_barcode's ``product_info`` unchanged
    (ingredients, Nutri-Score, NOVA, additives, allergens, other
    nutrients); when replacing a sheet, send it back or it is cleared.

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
        "portion_g": portion_g,
        "product_info": product_info,
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
    Name, brand, weight, the 8 values per 100 g and ``product_info``:
    everything else the product page gives (ingredients, allergens,
    additives, Nutri-Score, NOVA, fruits and vegetables %, levels, other
    nutrients). A proposal to check, then save_food with all of it.
    """
    return await client.get(f"/openfoodfacts/{barcode}")


@mcp.tool()
async def scan_barcode(photo_base64: str) -> Any:
    """Read a pack's barcode on a photo, decoded on the hub (offline).

    Returns the barcodes read, ``food`` (my food with that barcode, or
    null), ``product`` (an Open Food Facts proposal, only when the hub
    allows it; only the barcode is sent) and ``note``.
    """
    raw = base64.b64decode(photo_base64)
    files = {"file": ("code-barres.jpg", raw, "image/jpeg")}
    return await client.upload("/foods/scan", files, {})


@mcp.tool()
async def refresh_food(food_id: str) -> Any:
    """Read a saved food's Open Food Facts page again, by its barcode.

    No pack to scan again. Replaces the values Open Food Facts gives and
    the product details (Nutri-Score, NOVA, additives…), fills the
    package weight and brand when empty, keeps the user's own fields.
    Answers the sheet and ``changed`` (empty: nothing changed).
    """
    return await client.post(f"/foods/{food_id}/refresh")


@mcp.tool()
async def refresh_foods() -> Any:
    """Read again every saved food that has a barcode (a minute at most).

    ``updated``, ``unchanged``, ``failed`` (with the reason) and
    ``remaining`` (call again). The hub also does it by itself for pages
    older than FOOD_REFRESH_DAYS days.
    """
    return await client.post("/foods/refresh")


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
