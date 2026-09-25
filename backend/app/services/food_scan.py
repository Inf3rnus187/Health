"""A pack's barcode, photographed: which of my foods, or which product.

The code is read on the hub (:mod:`barcode_read`). A food of the user's
list with that barcode answers first (scan the sachet at meal time, the
food is found); else, only when ``FOOD_LOOKUP_ONLINE=true``, Open Food
Facts is asked for the product — a proposal for a new food sheet.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import InvalidInputError, NotFoundError
from app.models.food import Food
from app.schemas.food import FoodOut
from app.services import barcode_read, food_off


async def scan(
    session: AsyncSession, user_id: str, data: bytes
) -> dict[str, Any]:
    """The barcodes on the photo, the user's food, the online product."""
    online = get_settings().food_lookup_online
    codes = barcode_read.read(data)
    out: dict[str, Any] = {
        "barcodes": codes,
        "food": None,
        "product": None,
        "online": online,
        "note": "" if codes else "Aucun code-barres lisible sur la photo",
    }
    if not codes:
        return out
    food = await _mine(session, user_id, codes)
    if food is not None:
        out["food"] = FoodOut.of(food).model_dump(mode="json")
    elif online:
        out["product"], out["note"] = await _product(codes[0])
    return out


async def _mine(
    session: AsyncSession, user_id: str, codes: list[str]
) -> Food | None:
    """The user's food carrying one of these barcodes, if any."""
    rows = await session.execute(
        select(Food).where(Food.user_id == user_id, Food.barcode.in_(codes))
    )
    return rows.scalars().first()


async def _product(code: str) -> tuple[dict[str, Any] | None, str]:
    """Open Food Facts' proposal, or why there is none."""
    try:
        return await food_off.lookup(code), ""
    except (NotFoundError, InvalidInputError) as exc:
        return None, exc.message
