"""The stock of « Mes aliments »: purchases, losses, counts; what is left.

Only what comes in (a purchase), goes out other than eaten (thrown,
given) or is counted is entered; what the meals ate is read from their
analysis, so the level follows every meal changed, read again or
deleted. An iPhone Shortcut may pass its token as ``?token=``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.food_stock import StockIn, StockMoveOut
from app.services import audit, food_stock, foods, stock_level
from app.services.timed_entries import utc

router = APIRouter(prefix="/stock", tags=["journal"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]
WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.get("")
async def stock(principal: ReaderDep, session: SessionDep) -> dict[str, Any]:
    """What is left of each food with a stock.

    ``foods``: per food ``grams`` left (never below 0; ``missing`` says
    by how much the meals exceed what was entered — a count sets it
    right), ``packs`` / ``units`` / ``portions`` (that many packages,
    units or usual portions), ``eaten_g`` (what meals took since the
    last count, else since the first move), ``counted_at``,
    ``last_purchase``. ``pending_meals``: meals still being read, not
    counted yet. A meal with a price (delivery, expense report) never
    takes from the stock.
    """
    return await stock_level.levels(session, principal.user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add(
    body: StockIn, principal: TapDep, session: SessionDep
) -> dict[str, Any]:
    """Enter a purchase, a loss (thrown, given) or a count of one food.

    The food: ``food_id``, ``barcode`` (scanned on the pack) or ``food``
    (its name, a word's start is enough; two sizes answering the same
    name are refused: give the barcode). The quantity: ``packs`` (×
    the package), ``units`` (× the unit) or ``grams``; a purchase with
    none is one pack. ``kind``: ``purchase`` (default), ``out`` or
    ``count`` (what is left now: meals eaten before it no longer
    count). ``at``: when (default now; never more than 10 min ahead).
    Answers the move and the food's new level.
    """
    move = await food_stock.add(session, principal, body)
    food = await foods.get(session, principal.user.id, move.food_id)
    await audit.record(
        session,
        action="create",
        entity="food_stock_move",
        user_id=principal.user.id,
        entity_id=move.id,
        source=move.source,
        payload={"food": food.name, "kind": move.kind, "grams": move.grams},
    )
    await session.commit()
    now = await stock_level.levels(session, principal.user.id)
    here = [lv for lv in now["foods"] if lv["food_id"] == food.id]
    return {"move": StockMoveOut.model_validate(move), "level": here[0]}


@router.get("/{food_id}/moves")
async def moves(
    food_id: str, principal: ReaderDep, session: SessionDep
) -> dict[str, Any]:
    """A food's history: its moves (newest first) and the meals that ate it.

    ``eaten``: ``meal_id``, ``eaten_at``, ``grams`` of each meal since
    the food's first move (those before its last count no longer take
    from the stock).
    """
    found = await food_stock.moves(session, principal.user.id, food_id)
    start = min((utc(m.at) for m in found), default=None)
    eaten, _ = await stock_level.eaten_since(session, principal.user.id, start)
    return {
        "moves": [StockMoveOut.model_validate(m) for m in found],
        "eaten": [
            {"meal_id": mid, "eaten_at": at, "grams": grams}
            for fid, at, grams, mid in sorted(eaten, key=lambda e: e[1])
            if fid == food_id
        ][::-1],
    }


@router.delete("/moves/{move_id}")
async def delete(
    move_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, str]:
    """Delete a move entered by mistake (the audit log keeps it)."""
    move = await food_stock.delete(session, principal.user.id, move_id)
    await audit.record(
        session,
        action="delete",
        entity="food_stock_move",
        user_id=principal.user.id,
        entity_id=move_id,
        payload={"kind": move.kind, "grams": move.grams},
    )
    await session.commit()
    return {"detail": "deleted"}
