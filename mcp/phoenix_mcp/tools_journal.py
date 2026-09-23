"""Tools: the journal — urinations and meals (photo, AI reading)."""

from __future__ import annotations

import base64
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def log_urination(at: str | None = None) -> Any:
    """Record one urination (now, or ``at`` ISO date-time with offset)."""
    return await client.post("/journal/urination", {"at": at})


@mcp.tool()
async def list_urinations(day: str | None = None) -> Any:
    """A day's urinations (default today): count and times."""
    return await client.get("/journal/urination", {"day": day})


@mcp.tool()
async def delete_urination(entry_id: str) -> Any:
    """Delete one urination entry."""
    return await client.request("DELETE", f"/journal/urination/{entry_id}")


@mcp.tool()
async def log_meal(
    description: str,
    meal_type: str = "",
    eaten_at: str | None = None,
    photo_base64: str | None = None,
    photo_filename: str = "repas.jpg",
    price: float | None = None,
) -> Any:
    """Log a meal, then the AI reads it (minutes; poll get_meal).

    meal_type: breakfast, lunch, snack or dinner (empty: from the hour
    it was eaten). The description is
    authoritative (quantities, cooking, no fat…); an optional photo helps
    estimate portions. ``price``: what it cost (a delivery). Nutrients go
    to Apple's nutrition metrics.
    """
    data = {
        "meal_type": meal_type,
        "eaten_at": eaten_at or "",
        "description": description,
    }
    if price is not None:
        data["price"] = str(price)
    files = {}
    if photo_base64:
        raw = base64.b64decode(photo_base64)
        files["file"] = (photo_filename, raw, "image/jpeg")
    return await client.upload("/meals", files, data)


@mcp.tool()
async def list_meals(start: str | None = None, end: str | None = None) -> Any:
    """Meals with their reading (default: last 7 days)."""
    return await client.get("/meals", {"start": start, "end": end})


@mcp.tool()
async def get_meal(meal_id: str) -> Any:
    """One meal: foods, checked nutrients, score, verdict, remarks."""
    return await client.get(f"/meals/{meal_id}")


@mcp.tool()
async def update_meal(
    meal_id: str,
    description: str | None = None,
    meal_type: str | None = None,
    eaten_at: str | None = None,
) -> Any:
    """Correct a meal (text, type, time); it is read again."""
    body = {
        k: v
        for k, v in {
            "description": description,
            "meal_type": meal_type,
            "eaten_at": eaten_at,
        }.items()
        if v is not None
    }
    return await client.request("PUT", f"/meals/{meal_id}", body=body)


@mcp.tool()
async def analyze_meal(meal_id: str) -> Any:
    """Read a meal again with the current models."""
    return await client.post(f"/meals/{meal_id}/analyze")


@mcp.tool()
async def delete_meal(meal_id: str) -> Any:
    """Delete a meal, its photo and its nutrients."""
    return await client.request("DELETE", f"/meals/{meal_id}")
