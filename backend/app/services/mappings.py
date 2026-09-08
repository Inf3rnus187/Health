"""Resolve and manage external-key → metric-key mappings (§7.1)."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mapping import IngestMapping
from app.schemas.ingest import MappingCreate


async def resolve(
    session: AsyncSession,
    user_id: str,
    source: str,
    external_key: str,
) -> str | None:
    """Return the metric key for an external key (user over global)."""
    stmt = (
        select(IngestMapping)
        .where(
            IngestMapping.source == source,
            IngestMapping.external_key == external_key,
            or_(
                IngestMapping.user_id == user_id,
                IngestMapping.user_id.is_(None),
            ),
        )
        .order_by(IngestMapping.user_id.is_(None))
    )
    result = await session.execute(stmt)
    mapping = result.scalars().first()
    return mapping.metric_key if mapping else None


async def list_mappings(
    session: AsyncSession, user_id: str
) -> list[IngestMapping]:
    """Return the user's mappings plus the global defaults."""
    result = await session.execute(
        select(IngestMapping)
        .where(
            or_(
                IngestMapping.user_id == user_id,
                IngestMapping.user_id.is_(None),
            )
        )
        .order_by(IngestMapping.source, IngestMapping.external_key)
    )
    return list(result.scalars().all())


async def create_mapping(
    session: AsyncSession, user_id: str, data: MappingCreate
) -> IngestMapping:
    """Create a user-scoped mapping (overrides a global default)."""
    mapping = IngestMapping(
        user_id=user_id,
        source=data.source,
        external_key=data.external_key,
        metric_key=data.metric_key,
    )
    session.add(mapping)
    await session.flush()
    return mapping
