"""Events: open a grouping context and attach measurements to it."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.base import utcnow
from app.models.event import Event
from app.models.measurement import Measurement
from app.schemas.event import EventCreate
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure_service


async def create_event(
    session: AsyncSession, user_id: str, data: EventCreate
) -> Event:
    """Create an event, defaulting time and date when omitted."""
    occurred = data.occurred_at or utcnow()
    event = Event(
        user_id=user_id,
        type=data.type,
        occurred_at=occurred,
        date_key=data.date_key or occurred.date(),
        meta=data.meta,
        source=data.source,
    )
    session.add(event)
    await session.flush()
    return event


async def list_events(
    session: AsyncSession,
    user_id: str,
    *,
    event_type: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[Event]:
    """Return the user's events, newest first, matching filters."""
    stmt = select(Event).where(Event.user_id == user_id)
    if event_type is not None:
        stmt = stmt.where(Event.type == event_type)
    if start is not None:
        stmt = stmt.where(Event.date_key >= start)
    if end is not None:
        stmt = stmt.where(Event.date_key <= end)
    result = await session.execute(stmt.order_by(Event.occurred_at.desc()))
    return list(result.scalars().all())


async def attach_measurements(
    session: AsyncSession,
    user_id: str,
    event_id: str,
    items: list[MeasurementIn],
    *,
    source: str,
    token_id: str | None = None,
) -> list[Measurement]:
    """Record measurements bound to an existing event."""
    await _owned_event(session, user_id, event_id)
    return await measure_service.record_batch(
        session,
        user_id,
        items,
        source=source,
        token_id=token_id,
        event_id=event_id,
    )


async def _owned_event(
    session: AsyncSession, user_id: str, event_id: str
) -> Event:
    """Return the event if it belongs to ``user_id`` or raise."""
    event = await session.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise NotFoundError("Event not found")
    return event
