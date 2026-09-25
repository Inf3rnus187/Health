"""A food's stock moves: a purchase, a loss or a count, typed or scanned.

The food is found by its id, by a barcode scanned on the pack, or by its
name (accents and case ignored; the start of a word of 3 letters or more
is enough). Two sizes of one product answering the same name are not
guessed: the move asks for the barcode or the id. The quantity is kept
in grams: packs × the package, units × the unit (« 6 tomates »), or
grams; the words said are kept beside it.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import InvalidInputError, NotFoundError
from app.core.scopes import HUB_FULL
from app.models.base import utcnow
from app.models.food import Food
from app.models.food_stock import StockMove
from app.schemas.food_stock import StockIn
from app.services import foods
from app.services.daily_rollup import user_zone
from app.services.meal_foods import label
from app.services.text_norm import norm
from app.services.timed_entries import utc

_FUTURE = timedelta(minutes=10)
_SHORTEST_PART = 3


async def add(
    session: AsyncSession, who: Principal, data: StockIn
) -> StockMove:
    """Record one move of one of the user's foods."""
    food = await find_food(session, who.user.id, data)
    grams, said = _quantity(food, data)
    at = data.at or utcnow()
    if at.tzinfo is None:  # a local time typed in a form
        at = at.replace(tzinfo=await user_zone(session, who.user.id))
    if utc(at) > utcnow() + _FUTURE:
        raise InvalidInputError("A stock move cannot be in the future")
    move = StockMove(
        user_id=who.user.id,
        food_id=food.id,
        at=utc(at),
        kind=data.kind,
        grams=round(grams, 1),
        said=said[:80],
        note=data.note.strip(),
        source=_channel(who),
    )
    session.add(move)
    await session.flush()
    return move


async def find_food(session: AsyncSession, user_id: str, data: StockIn) -> Food:
    """The food a move is about: id, else barcode, else name (or 404)."""
    if data.food_id:
        return await foods.get(session, user_id, data.food_id)
    known = await foods.list_foods(session, user_id)
    if data.barcode:
        found = [f for f in known if f.barcode == data.barcode]
        if not found:
            raise NotFoundError(f"No food with barcode {data.barcode}")
        return found[0]
    if not data.food:
        raise InvalidInputError("Give food_id, barcode or food (its name)")
    return _named(known, data.food)


async def moves(
    session: AsyncSession, user_id: str, food_id: str
) -> list[StockMove]:
    """A food's moves, newest first (404 for another user's food)."""
    await foods.get(session, user_id, food_id)
    rows = await session.execute(
        select(StockMove)
        .where(StockMove.user_id == user_id, StockMove.food_id == food_id)
        .order_by(StockMove.at.desc())
    )
    return list(rows.scalars())


async def delete(
    session: AsyncSession, user_id: str, move_id: str
) -> StockMove:
    """Delete one of the user's moves (a mistake; the audit log keeps it)."""
    move = await session.get(StockMove, move_id)
    if move is None or move.user_id != user_id:
        raise NotFoundError("Stock move not found")
    await session.delete(move)
    await session.flush()
    return move


def _named(known: list[Food], name: str) -> Food:
    """The one food called so (a whole name, else a word's start)."""
    wanted = norm(name)
    found = [f for f in known if wanted in (norm(f.name), norm(label(f)))]
    if not found and len(wanted) >= _SHORTEST_PART:
        found = [f for f in known if f" {wanted}" in f" {norm(label(f))}"]
    if not found:
        raise NotFoundError(f"No food called « {name} »")
    if len(found) > 1:
        names = " ; ".join(label(f) for f in found)
        raise InvalidInputError(f"Several foods fit « {name} » : {names}")
    return found[0]


def _quantity(food: Food, data: StockIn) -> tuple[float, str]:
    """Grams, and the words said: grams, units or packs (1 pack bought)."""
    if data.grams is not None:
        grams, said = data.grams, f"{data.grams:g} g"
    elif data.units is not None:
        if not food.unit_g:
            raise InvalidInputError("This food has no unit weight")
        grams = data.units * food.unit_g
        said = f"{data.units:g} × {food.unit_name or 'unité'}"
    else:
        packs = data.packs if data.packs is not None else _one(data.kind)
        if not food.package_g:
            raise InvalidInputError("This food has no package weight")
        grams, said = (
            packs * food.package_g,
            f"{packs:g} × {food.package_g:g} g",
        )
    if grams <= 0 and data.kind != "count":
        raise InvalidInputError("A purchase or a loss needs a quantity")
    return grams, said


def _one(kind: str) -> float:
    """No quantity: one pack bought; a loss or a count must say it."""
    if kind != "purchase":
        raise InvalidInputError("Give packs, units or grams")
    return 1.0


def _channel(who: Principal) -> str:
    """How the move came in: web, mcp or raccourci (another token)."""
    if who.source == "jwt":
        return "web"
    return "mcp" if HUB_FULL in who.scopes else "raccourci"
