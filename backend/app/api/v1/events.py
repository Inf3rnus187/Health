"""Event endpoints: open a context and attach measurements to it."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import (
    Principal,
    PrincipalDep,
    SessionDep,
    require_scope,
)
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.event import Event
from app.models.measurement import Measurement
from app.schemas.event import EventCreate, EventOut
from app.schemas.measurement import MeasurementBatch, MeasurementOut
from app.services import audit
from app.services import events as svc

router = APIRouter(prefix="/events", tags=["events"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: EventCreate, principal: WriteDep, session: SessionDep
) -> Event:
    """Open a new event (day, night, workout block, capture...)."""
    event = await svc.create_event(session, principal.user.id, body)
    await audit.record(
        session,
        action="create",
        entity="event",
        user_id=principal.user.id,
        entity_id=event.id,
    )
    await session.commit()
    return event


@router.post(
    "/{event_id}/measurements",
    response_model=list[MeasurementOut],
    status_code=status.HTTP_201_CREATED,
)
async def attach(
    event_id: str,
    body: MeasurementBatch,
    principal: WriteDep,
    session: SessionDep,
) -> list[Measurement]:
    """Attach measurements to an existing event."""
    is_user = principal.source == "jwt"
    rows = await svc.attach_measurements(
        session,
        principal.user.id,
        event_id,
        body.items,
        source="manual" if is_user else "script",
        token_id=principal.token_id,
    )
    await session.commit()
    return rows


@router.get("", response_model=list[EventOut])
async def index(
    principal: PrincipalDep,
    session: SessionDep,
    event_type: Annotated[str | None, Query()] = None,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[Event]:
    """Return the user's events, newest first."""
    return await svc.list_events(
        session,
        principal.user.id,
        event_type=event_type,
        start=start,
        end=end,
    )
