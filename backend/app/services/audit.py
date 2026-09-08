"""Audit-log writer shared by every state-changing service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record(
    session: AsyncSession,
    *,
    action: str,
    entity: str,
    user_id: str | None = None,
    entity_id: str | None = None,
    actor: str = "user",
    source: str = "api",
    payload: dict[str, Any] | None = None,
) -> None:
    """Append one audit record (the caller owns the commit)."""
    session.add(
        AuditLog(
            user_id=user_id,
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            source=source,
            payload=payload,
        )
    )
