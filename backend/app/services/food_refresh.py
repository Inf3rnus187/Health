"""Read a food's Open Food Facts page again, by the barcode it keeps.

No need to find the pack again: the sheet's barcode is enough. Only
what comes from Open Food Facts is replaced — the values it gives (one
it leaves empty is kept), the product details, the package weight and
the brand when the sheet has none. The user's own fields stay: name,
units, usual portion, other names, note, photos. Meals already read
keep their reading (« Réanalyser » applies the new values).

``refresh_stale`` is the worker's daily job: sheets not read for
``FOOD_REFRESH_DAYS`` days (0: never), a few at a time, one second
apart, only when ``FOOD_LOOKUP_ONLINE=true``.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, InvalidInputError
from app.models.food import Food
from app.services import food_off, foods

_BUDGET_S = 60.0  # one « Tout relire » answers within a minute
_PER_RUN = 50
_PAUSE_S = 1.0


async def refresh(food: Food) -> list[str]:
    """Read the food's page again; the fields that changed."""
    if not food.barcode:
        raise InvalidInputError("Cette fiche n'a pas de code-barres")
    found = await food_off.lookup(food.barcode)
    return _merge(food, found)


async def refresh_all(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Every sheet of the user with a barcode, within about a minute."""
    coded = [f for f in await foods.list_foods(session, user_id) if f.barcode]
    start = time.monotonic()
    done: dict[str, Any] = {"updated": [], "unchanged": 0, "failed": []}
    for i, food in enumerate(coded):
        if time.monotonic() - start > _BUDGET_S:
            done["remaining"] = len(coded) - i
            break
        await _one(food, done)
    await session.flush()
    return {"remaining": 0, **done}


async def refresh_stale(session: AsyncSession, days: int) -> int:
    """The worker's job: sheets not read for ``days`` days (all users)."""
    if days <= 0 or not get_settings().food_lookup_online:
        return 0
    rows = await session.execute(select(Food).where(Food.barcode != ""))
    limit = (datetime.now(UTC) - timedelta(days=days)).date().isoformat()
    stale = [f for f in rows.scalars() if _read_on(f) < limit][:_PER_RUN]
    for food in stale:
        await _one(food, {"updated": [], "unchanged": 0, "failed": []})
        await session.commit()
        await asyncio.sleep(_PAUSE_S)
    return len(stale)


async def _one(food: Food, done: dict[str, Any]) -> None:
    """Refresh one sheet, counting the outcome."""
    try:
        changed = await refresh(food)
    except AppError as exc:
        done["failed"].append({"name": food.name, "reason": exc.message})
        return
    if changed:
        done["updated"].append({"name": food.name, "changed": changed})
    else:
        done["unchanged"] += 1


def _merge(food: Food, found: dict[str, Any]) -> list[str]:
    """Put Open Food Facts' fields on the sheet; what changed."""
    per = dict(food.per_100g or {})
    changed = [k for k, v in found["per_100g"].items() if per.get(k) != v]
    if changed:
        food.per_100g = {**per, **found["per_100g"]}
        food.source = found["source"]
    info = found.get("product_info") or {}
    if _details(info) != _details(food.product_info or {}):
        changed.append("product_info")
    food.product_info = info  # its reading date moves on anyway
    if not food.package_g and found.get("package_g"):
        food.package_g = found["package_g"]
        changed.append("package_g")
    if not food.brand and found.get("brand"):
        food.brand = found["brand"]
        changed.append("brand")
    return changed


def _details(info: dict[str, Any]) -> dict[str, Any]:
    """The product details without their reading date."""
    return {k: v for k, v in info.items() if k != "fetched_at"}


def _read_on(food: Food) -> str:
    """When the sheet's page was last read (ISO date; never: empty)."""
    return str((food.product_info or {}).get("fetched_at") or "")
