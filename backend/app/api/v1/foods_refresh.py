"""Read the Open Food Facts page of saved foods again, by their barcode.

No pack to find again: the sheet keeps its barcode. Only what comes
from Open Food Facts changes (see ``food_refresh``); needs
``FOOD_LOOKUP_ONLINE=true``, only the barcode leaves the hub.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.deps import Principal, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.food import FoodOut
from app.services import audit, food_refresh, foods

router = APIRouter(prefix="/foods", tags=["journal"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("/refresh")
async def refresh_all(
    principal: WriteDep, session: SessionDep
) -> dict[str, Any]:
    """Read again every sheet that has a barcode (about a minute at most).

    Answers ``updated`` (name and ``changed`` fields of each sheet that
    changed), ``unchanged`` (how many), ``failed`` (name and reason:
    product gone, lookup disabled…) and ``remaining`` (sheets left for
    lack of time: call again).
    """
    done = await food_refresh.refresh_all(session, principal.user.id)
    await audit.record(
        session,
        action="refresh",
        entity="food",
        user_id=principal.user.id,
        payload={
            "updated": len(done["updated"]),
            "failed": len(done["failed"]),
        },
    )
    await session.commit()
    return done


@router.post("/{food_id}/refresh")
async def refresh(
    food_id: str, principal: WriteDep, session: SessionDep
) -> dict[str, Any]:
    """Read one sheet's Open Food Facts page again, by its barcode.

    Replaces the values Open Food Facts gives, the product details, the
    package weight and brand when empty; keeps the user's own fields.
    Answers the sheet and ``changed``: ``energy_kcal`` … ``sodium_mg``,
    ``product_info``, ``package_g``, ``brand`` (empty: nothing changed).
    """
    food = await foods.get(session, principal.user.id, food_id)
    changed = await food_refresh.refresh(food)
    await audit.record(
        session,
        action="refresh",
        entity="food",
        user_id=principal.user.id,
        entity_id=food.id,
        payload={"changed": changed},
    )
    await session.commit()
    await session.refresh(food)
    return {"food": FoodOut.of(food), "changed": changed}
