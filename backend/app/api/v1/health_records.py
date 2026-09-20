"""List and download imported workouts, ECG traces and GPS routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import PrincipalDep, SessionDep
from app.models.health_raw import EcgRecord, RouteFile, Workout
from app.schemas.health_raw import EcgOut, RouteOut, WorkoutOut
from app.services import health_records as svc

router = APIRouter(tags=["health-records"])


@router.get("/workouts", response_model=list[WorkoutOut])
async def workouts(
    principal: PrincipalDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Workout]:
    """List the caller's workouts, newest first."""
    return await svc.list_workouts(session, principal.user.id, limit, offset)


@router.get("/ecg", response_model=list[EcgOut])
async def ecg(principal: PrincipalDep, session: SessionDep) -> list[EcgRecord]:
    """List the caller's ECG records."""
    return await svc.list_ecg(session, principal.user.id)


@router.get("/routes", response_model=list[RouteOut])
async def routes(
    principal: PrincipalDep, session: SessionDep
) -> list[RouteFile]:
    """List the caller's GPS routes."""
    return await svc.list_routes(session, principal.user.id)


@router.get("/ecg/{record_id}/file")
async def ecg_file(
    record_id: str, principal: PrincipalDep, session: SessionDep
) -> Response:
    """Download one ECG trace as CSV."""
    data = await svc.ecg_bytes(session, principal.user.id, record_id)
    return Response(content=data, media_type="text/csv")


@router.get("/routes/{record_id}/file")
async def route_file(
    record_id: str, principal: PrincipalDep, session: SessionDep
) -> Response:
    """Download one route as GPX."""
    data = await svc.route_bytes(session, principal.user.id, record_id)
    return Response(content=data, media_type="application/gpx+xml")
