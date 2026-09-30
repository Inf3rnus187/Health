"""Dashboard endpoint: per-domain plottable series (§10)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.core.deps import ReaderDep, SessionDep
from app.core.responses import model_json
from app.schemas.dashboard import DashboardOut
from app.services import dashboard as svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{domain}", response_model=DashboardOut)
async def domain_dashboard(
    domain: str,
    principal: ReaderDep,
    session: SessionDep,
    window: Annotated[int, Query(ge=1, le=365)] = 7,
) -> Response:
    """Return rolling series for every numeric metric of a domain.

    Every day of the history, each point the trailing ``window`` days'
    aggregate (the metric's own: mean, sum, min, max or last).
    """
    board = await svc.get_dashboard(session, principal.user.id, domain, window)
    return model_json(board)
