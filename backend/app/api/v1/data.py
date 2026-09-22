"""Data inventory and reconciliation (everything stored, one truth)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.core.deps import SessionDep, UserDep
from app.services import inventory as svc
from app.workers.queue import enqueue

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/inventory")
async def inventory(
    principal: UserDep, session: SessionDep
) -> list[dict[str, Any]]:
    """Every metric with data: raw samples and daily values per source."""
    return await svc.inventory(session, principal.user.id)


@router.post("/reconcile", status_code=status.HTTP_202_ACCEPTED)
async def reconcile(principal: UserDep) -> dict[str, bool]:
    """Queue: merge duplicate keys, rebuild daily values from raw data."""
    queued = await enqueue("reconcile_data", principal.user.id)
    return {"queued": queued}
