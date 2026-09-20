"""CRUD and .ics import for medical appointments (rendez-vous)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.medical import Appointment
from app.schemas.care import AppointmentIn
from app.services.ics import parse_events


async def create(
    session: AsyncSession, user_id: str, data: AppointmentIn
) -> Appointment:
    """Create a manual appointment."""
    row = Appointment(user_id=user_id, source="manual", **data.model_dump())
    session.add(row)
    await session.flush()
    return row


async def list_all(session: AsyncSession, user_id: str) -> list[Appointment]:
    """Return the user's appointments, soonest-first by start time."""
    result = await session.execute(
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .order_by(Appointment.starts_at.desc())
    )
    return list(result.scalars().all())


async def delete(session: AsyncSession, user_id: str, aid: str) -> None:
    """Delete one of the user's appointments."""
    row = await session.get(Appointment, aid)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Appointment not found")
    await session.delete(row)
    await session.flush()


async def import_ics(session: AsyncSession, user_id: str, text: str) -> int:
    """Import VEVENTs from an .ics file, skipping already-seen UIDs."""
    seen = await _existing_uids(session, user_id)
    added = 0
    for event in parse_events(text):
        uid = event.get("uid")
        if uid and uid in seen:
            continue
        session.add(_from_event(user_id, event))
        if uid:
            seen.add(uid)
        added += 1
    await session.flush()
    return added


async def _existing_uids(session: AsyncSession, user_id: str) -> set[str]:
    """Return the UIDs already imported for this user."""
    result = await session.execute(
        select(Appointment.external_uid).where(
            Appointment.user_id == user_id,
            Appointment.external_uid.is_not(None),
        )
    )
    return {uid for (uid,) in result.all() if uid}


def _from_event(user_id: str, event: dict[str, Any]) -> Appointment:
    """Build an Appointment row from a parsed .ics event."""
    return Appointment(
        user_id=user_id,
        title=event["title"],
        starts_at=event["starts_at"],
        ends_at=event.get("ends_at"),
        location=event.get("location"),
        source="ics",
        external_uid=event.get("uid"),
    )
