"""Liveness/readiness probe (mounted outside the versioned prefix)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    """Return service status and confirm database connectivity."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}
