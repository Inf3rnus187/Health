"""Browse CDA clinical observations and fetch the stored document."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.errors import NotFoundError
from app.models.health_raw import ClinicalDocument, ClinicalObservation


async def page(
    session: AsyncSession,
    user_id: str,
    *,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ClinicalObservation], int]:
    """Return a page of observations and the total that match."""
    stmt = select(ClinicalObservation).where(
        ClinicalObservation.user_id == user_id
    )
    if search:
        stmt = stmt.where(ClinicalObservation.label.ilike(f"%{search}%"))
    total = await _count(session, stmt)
    ordered = stmt.order_by(ClinicalObservation.effective_at.desc())
    result = await session.execute(ordered.limit(limit).offset(offset))
    return list(result.scalars().all()), total


async def document(
    session: AsyncSession, user_id: str
) -> ClinicalDocument | None:
    """Return the user's stored CDA document, if any."""
    result = await session.execute(
        select(ClinicalDocument)
        .where(ClinicalDocument.user_id == user_id)
        .order_by(ClinicalDocument.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def document_bytes(session: AsyncSession, user_id: str) -> bytes:
    """Return the decrypted raw CDA XML for the user."""
    doc = await document(session, user_id)
    if doc is None:
        raise NotFoundError("No clinical document")
    return crypto.decrypt(Path(doc.file_path).read_bytes())


async def _count(
    session: AsyncSession, stmt: Select[tuple[ClinicalObservation]]
) -> int:
    """Count the rows a filtered statement would return."""
    counter = select(func.count()).select_from(stmt.subquery())
    return int((await session.execute(counter)).scalar_one())
