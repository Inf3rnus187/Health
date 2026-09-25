"""Tools: the journal — day lines, urinations and meals (photo, AI)."""

from __future__ import annotations

import base64
import json
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def journal_days(
    start: str | None = None,
    end: str | None = None,
    limit: int = 31,
    offset: int = 0,
) -> Any:
    """The daily journal, one line per day (newest first), paged.

    Per day: the night ended that morning (minutes asleep, ``blocks`` =
    in how many goes, awakenings, bedtime → wake-up), water (bottles of
    1.5 L and litres), coffees, cigarettes, pees, meals (count, energy).
    ``start`` / ``end``: YYYY-MM-DD (default: from the first day recorded
    up to today); ``total`` is the number of days of the period.
    """
    return await client.get(
        "/journal/days",
        {"start": start, "end": end, "limit": limit, "offset": offset},
    )


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
    more_photos_base64: list[str] | None = None,
    foods: list[dict[str, Any]] | None = None,
) -> Any:
    """Log a meal, then the AI reads it (minutes; poll get_meal).

    Call list_foods first. ``description``: the user's own words, with
    their quantities (« 2 tomates, un pavé de saumon »), never a summary:
    the hub reads the grams in it. ``foods``: the foods of the user's
    list they name, as ``[{"food_id": "…", "grams": null}]`` (grams only
    when said; null: read from the description — « un pavé » = the
    food's unit, « une boîte » = its package — else estimated); they are
    computed from their label. A food the description names is found
    anyway (its name, an alias, or « pavé de saumon » for « Saumon
    sauvage rose »). meal_type: breakfast, lunch, snack or dinner, only
    when the user says it (empty: from the hour eaten). ``eaten_at``:
    ISO time when not now. An optional photo helps estimate portions;
    ``more_photos_base64``: up to 6 more pictures (the box, the sachet,
    its nutrition table), whose labels are read. Nutrients go to Apple's
    nutrition metrics. In get_meal, an item's ``source`` says where its
    values come from: "étiquette" (the user's sheet), "Ciqual", or none
    (the model's estimate).

    Health follow-up only: never a work proof, no price. A meal paid
    for (receipt, delivery, expense report) is a proof: add_evidence
    with kind « repas » or « livraison » and trace={"amount": …,
    "meal": True} — it logs the meal here too.
    """
    data = {
        "meal_type": meal_type,
        "eaten_at": eaten_at or "",
        "description": description,
        "foods": json.dumps(foods) if foods else "",
    }
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    if photo_base64:
        raw = base64.b64decode(photo_base64)
        files.append(("file", (photo_filename, raw, "image/jpeg")))
    for i, more in enumerate(more_photos_base64 or [], start=1):
        raw = base64.b64decode(more)
        files.append(("photos", (f"photo_{i}.jpg", raw, "image/jpeg")))
    return await client.upload("/meals", files, data)


@mcp.tool()
async def list_meals(start: str | None = None, end: str | None = None) -> Any:
    """Meals with their reading (default: last 7 days)."""
    return await client.get("/meals", {"start": start, "end": end})


@mcp.tool()
async def get_meal(meal_id: str) -> Any:
    """One meal: foods, checked nutrients, score, verdict, remarks.

    ``reference`` (computed by the hub): each nutrient against the
    official daily reference (``day``, ``day_pct``) and the meal type's
    indicative part of the day (``low``–``high``, ``verdict`` below /
    within / above; none for a snack). See nutrition_references.
    """
    return await client.get(f"/meals/{meal_id}")


@mcp.tool()
async def update_meal(
    meal_id: str,
    description: str | None = None,
    meal_type: str | None = None,
    eaten_at: str | None = None,
    foods: list[dict[str, Any]] | None = None,
) -> Any:
    """Correct a meal (text, type, time, foods of the list); read again.

    ``foods`` replaces the list's foods eaten (``[]`` removes them).
    """
    body = {
        k: v
        for k, v in {
            "description": description,
            "meal_type": meal_type,
            "eaten_at": eaten_at,
            "foods": foods,
        }.items()
        if v is not None
    }
    return await client.request("PUT", f"/meals/{meal_id}", body=body)


@mcp.tool()
async def add_meal_photo(
    meal_id: str, photo_base64: str, filename: str = "photo.jpg"
) -> Any:
    """Add a photo to a meal afterwards; it is read again.

    A meal without a photo gets it as the plate's; otherwise it joins the
    others (the box, the sachet, its nutrition table; 6 at most).
    """
    raw = base64.b64decode(photo_base64)
    files = {"file": (filename, raw, "image/jpeg")}
    return await client.upload(f"/meals/{meal_id}/photos", files, {})


@mcp.tool()
async def delete_meal_photo(meal_id: str, photo_id: str | None = None) -> Any:
    """Delete a meal's photo; the meal is read again.

    ``photo_id``: one of its ``photo_ids``; none: the plate's photo.
    """
    path = (
        f"/meals/{meal_id}/photos/{photo_id}"
        if photo_id
        else f"/meals/{meal_id}/photo"
    )
    return await client.request("DELETE", path)


@mcp.tool()
async def analyze_meal(meal_id: str) -> Any:
    """Read a meal again with the current models."""
    return await client.post(f"/meals/{meal_id}/analyze")


@mcp.tool()
async def delete_meal(meal_id: str) -> Any:
    """Delete a meal, its photo and its nutrients."""
    return await client.request("DELETE", f"/meals/{meal_id}")
