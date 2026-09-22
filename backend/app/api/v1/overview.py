"""One metric at a glance (the numbers every page shows)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import PrincipalDep, SessionDep
from app.services import metric_overview

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/{key}/overview")
async def overview(
    key: str,
    principal: PrincipalDep,
    session: SessionDep,
    days: Annotated[int, Query(ge=7, le=36500)] = 365,
) -> dict[str, Any]:
    """Latest reading, day value, averages, sources and daily series."""
    return await metric_overview.overview(session, principal.user.id, key, days)
