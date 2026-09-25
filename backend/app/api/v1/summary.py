"""Home-page summary endpoint: latest value of headline metrics."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import ReaderDep, SessionDep
from app.schemas.summary import TileOut
from app.services import summary as svc

router = APIRouter(tags=["summary"])


@router.get("/summary", response_model=list[TileOut])
async def summary(principal: ReaderDep, session: SessionDep) -> list[TileOut]:
    """Return the latest value of each available headline metric.

    Each tile: ``value`` of its last day (``date_key``), ``at`` the time
    of the last reading when known (a counter: its last addition that
    day; null for a value entered afterwards for its day), ``delta``,
    ``avg7``, ``spark``. ``nutrition.energy`` (« Énergie apportée
    (repas) »): the day's kcal from analysed meals (and Apple Health),
    beside ``activity.active_energy`` and ``activity.basal_energy``.
    """
    tiles = await svc.headline(session, principal.user.id)
    return [TileOut(**tile._asdict()) for tile in tiles]
