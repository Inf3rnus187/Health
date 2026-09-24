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
) -> Any:
    """Add a food (or replace ``food_id``'s sheet).

    ``per_100g``: energy_kcal, protein_g, carbs_g, sugars_g, fat_g,
    sat_fat_g, fiber_g, sodium_mg (1 g of salt = 400 mg of sodium).
    ``aliases``: other names used in meals, comma separated.
    """
    body = {
        "name": name,
        "brand": brand,
        "aliases": aliases,
        "package_g": package_g,
        "per_100g": per_100g or {},
        "note": note,
    }
    if food_id:
        return await client.request("PUT", f"/foods/{food_id}", body=body)
    return await client.post("/foods", body)


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
