"""How much of each food is left: counted, bought, thrown, eaten.

For one food: its last count (« il m'en reste 1 boîte ») is the base,
then the purchases and losses entered after it, then the meals eaten
after it — or, without a count, everything since its first move. What
a meal ate is its analysed lines of that food (source « étiquette »,
the grams the reading used); a meal bought (with a price: a delivery,
an expense report) does not take from the stock, nor a meal still
being read. So a meal changed, read again or deleted changes the stock.
Below zero, the level shows 0 and ``missing`` says by how much the meals
exceed what was entered: a count sets it right.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food import Food
from app.models.food_stock import StockMove
from app.models.meal import Meal
from app.services import foods
from app.services.meal_foods import label
from app.services.timed_entries import utc

Eaten = tuple[str, datetime, float, str]  # food, when, grams, meal id
_PENDING = ("queued", "running")


async def levels(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Every food with a stock, and how many meals are still being read."""
    rows = await session.execute(
        select(StockMove)
        .where(StockMove.user_id == user_id)
        .order_by(StockMove.at)
    )
    by_food: dict[str, list[StockMove]] = defaultdict(list)
    for move in rows.scalars():
        by_food[move.food_id].append(move)
    known = {f.id: f for f in await foods.list_foods(session, user_id)}
    start = min((utc(m[0].at) for m in by_food.values()), default=None)
    eaten, pending = await eaten_since(session, user_id, start)
    found = [level(known[fid], moves, eaten) for fid, moves in by_food.items()]
    return {
        "foods": sorted(found, key=lambda lv: lv["name"]),
        "pending_meals": pending,
    }


async def eaten_since(
    session: AsyncSession, user_id: str, start: datetime | None
) -> tuple[list[Eaten], int]:
    """The foods of « Mes aliments » the meals ate since ``start``."""
    if start is None:
        return [], 0
    rows = await session.execute(
        select(Meal).where(
            Meal.user_id == user_id,
            Meal.eaten_at >= start,
            Meal.price.is_(None),
        )
    )
    eaten: list[Eaten] = []
    pending = 0
    for meal in rows.scalars():
        pending += meal.analysis_status in _PENDING
        if meal.analysis_status == "done" and meal.analysis:
            eaten += _lines(meal)
    return eaten, pending


def level(
    food: Food, moves: list[StockMove], eaten: list[Eaten]
) -> dict[str, Any]:
    """One food's level from its moves (oldest first) and the meals."""
    counts = [m for m in moves if m.kind == "count"]
    base = counts[-1] if counts else None
    since = utc(base.at) if base else None
    start = utc(moves[0].at)
    left = base.grams if base else 0.0
    for move in moves:
        if move.kind != "count" and (since is None or utc(move.at) > since):
            left += move.grams if move.kind == "purchase" else -move.grams
    used = sum(
        grams
        for fid, at, grams, _ in eaten
        if fid == food.id and at >= start and (since is None or at > since)
    )
    return _described(food, left - used, used, moves, since)


def _described(
    food: Food,
    left: float,
    used: float,
    moves: list[StockMove],
    since: datetime | None,
) -> dict[str, Any]:
    """The level with what a person or an assistant needs to read it."""
    grams = max(0.0, round(left, 1))
    bought = [utc(m.at) for m in moves if m.kind == "purchase"]
    return {
        "food_id": food.id,
        "name": label(food),
        "grams": grams,
        "missing": round(-left, 1) if left < 0 else 0.0,
        "eaten_g": round(used, 1),
        "package_g": food.package_g,
        "packs": round(grams / food.package_g, 2) if food.package_g else None,
        "unit_name": food.unit_name,
        "units": round(grams / food.unit_g, 1) if food.unit_g else None,
        "portion_g": food.portion_g,
        "portions": round(grams / food.portion_g, 1)
        if food.portion_g
        else None,
        "counted_at": since,
        "last_purchase": max(bought) if bought else None,
    }


def _lines(meal: Meal) -> list[Eaten]:
    """The meal's lines computed from a sheet of « Mes aliments »."""
    at = utc(meal.eaten_at)
    return [
        (str(item["food_id"]), at, float(item.get("grams") or 0), meal.id)
        for item in (meal.analysis or {}).get("items") or []
        if isinstance(item, dict)
        and item.get("food_id")
        and item.get("source") == "étiquette"
    ]
