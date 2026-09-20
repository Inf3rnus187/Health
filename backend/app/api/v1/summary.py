"""Home-page summary endpoint: latest value of headline metrics."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import PrincipalDep, SessionDep
from app.schemas.summary import TileOut
from app.services import summary as svc

router = APIRouter(tags=["summary"])


@router.get("/summary", response_model=list[TileOut])
async def summary(
    principal: PrincipalDep, session: SessionDep
) -> list[TileOut]:
    """Return the latest value of each available headline metric."""
    tiles = await svc.headline(session, principal.user.id)
    return [
        TileOut(
            key=tile.key,
            label=tile.label,
            unit=tile.unit,
            value=tile.value,
            date_key=tile.date_key,
            at=tile.at,
        )
        for tile in tiles
    ]
