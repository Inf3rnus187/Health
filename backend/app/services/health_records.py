"""List workouts, ECG records and routes; read their stored files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.errors import NotFoundError
from app.models.health_raw import EcgRecord, RouteFile, Workout


async def list_workouts(
    session: AsyncSession, user_id: str, limit: int, offset: int
) -> list[Workout]:
    """Return the user's workouts, newest first."""
    result = await session.execute(
        select(Workout)
        .where(Workout.user_id == user_id)
        .order_by(Workout.start_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_ecg(session: AsyncSession, user_id: str) -> list[EcgRecord]:
    """Return the user's ECG records, newest first."""
    result = await session.execute(
        select(EcgRecord)
        .where(EcgRecord.user_id == user_id)
        .order_by(EcgRecord.recorded_at.desc())
    )
    return list(result.scalars().all())


async def list_routes(session: AsyncSession, user_id: str) -> list[RouteFile]:
    """Return the user's GPS routes, newest first."""
    result = await session.execute(
        select(RouteFile)
        .where(RouteFile.user_id == user_id)
        .order_by(RouteFile.started_at.desc())
    )
    return list(result.scalars().all())


async def ecg_bytes(
    session: AsyncSession, user_id: str, record_id: str
) -> bytes:
    """Return the decrypted CSV bytes of one ECG record."""
    row = await _owned(session, EcgRecord, user_id, record_id)
    return crypto.decrypt(_read(row.file_path))


async def route_bytes(
    session: AsyncSession, user_id: str, record_id: str
) -> bytes:
    """Return the decrypted GPX bytes of one route."""
    row = await _owned(session, RouteFile, user_id, record_id)
    return crypto.decrypt(_read(row.file_path))


async def _owned(
    session: AsyncSession, model: Any, user_id: str, record_id: str
) -> Any:
    """Fetch a record and confirm it belongs to the user."""
    row = await session.get(model, record_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Record not found")
    return row


def _read(path: str) -> bytes:
    """Read the raw file bytes from disk."""
    return Path(path).read_bytes()
