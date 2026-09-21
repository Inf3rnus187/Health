"""Browse CDA clinical observations and fetch the stored document."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy import Select, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.base import new_uuid, utcnow
from app.models.health_raw import ClinicalDocument, ClinicalObservation
from app.services.apple_health.cda import Observation, iter_observations

_settings = get_settings()


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


async def import_cda(
    session: AsyncSession, user_id: str, data: bytes
) -> dict[str, int]:
    """Import a doctor-delivered CDA: store observations + the document."""
    rows = [_obs_row(user_id, obs) for obs in iter_observations(BytesIO(data))]
    if rows:
        await session.execute(insert(ClinicalObservation), rows)
    path = _save(user_id, data)
    session.add(
        ClinicalDocument(
            user_id=user_id,
            file_path=str(path),
            observation_count=len(rows),
            source="cda",
        )
    )
    await session.flush()
    return {"observations": len(rows)}


async def _count(
    session: AsyncSession, stmt: Select[tuple[ClinicalObservation]]
) -> int:
    """Count the rows a filtered statement would return."""
    counter = select(func.count()).select_from(stmt.subquery())
    return int((await session.execute(counter)).scalar_one())


def _obs_row(user_id: str, obs: Observation) -> dict[str, Any]:
    """Build one clinical_observations insert row (source=cda)."""
    return {
        "id": new_uuid(),
        "user_id": user_id,
        "label": obs.label,
        "value_num": obs.value_num,
        "value_text": obs.value_text,
        "unit": obs.unit,
        "effective_at": obs.effective_at,
        "source": "cda",
        "created_at": utcnow(),
    }


def _save(user_id: str, data: bytes) -> Path:
    """Write the encrypted CDA XML to disk and return its path."""
    base = Path(_settings.media_dir) / user_id / "cda"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{new_uuid()}.xml"
    path.write_bytes(crypto.encrypt(data))
    return path
