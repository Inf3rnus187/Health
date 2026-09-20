"""Signal endpoints: ECG voltage series and GPS route tracks."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import PrincipalDep, SessionDep
from app.schemas.health_raw import EcgSeries, RouteTrack
from app.services import ecg as ecg_svc
from app.services import routes as route_svc

router = APIRouter(tags=["waveforms"])


@router.get("/ecg/{record_id}/series", response_model=EcgSeries)
async def ecg_series(
    record_id: str, principal: PrincipalDep, session: SessionDep
) -> EcgSeries:
    """Return one ECG's downsampled voltage trace."""
    rate, values = await ecg_svc.series(session, principal.user.id, record_id)
    return EcgSeries(sample_rate_hz=rate, values=values)


@router.get("/routes/{record_id}/track", response_model=RouteTrack)
async def route_track(
    record_id: str, principal: PrincipalDep, session: SessionDep
) -> RouteTrack:
    """Return one route's coordinates for drawing."""
    points = await route_svc.track(session, principal.user.id, record_id)
    return RouteTrack(points=points)
