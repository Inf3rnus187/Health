"""One metric at a glance (the numbers every page shows).

Served twice: ``/metrics/{key}/overview`` for API clients, scripts and
the MCP server, and ``/catalog/{key}/overview`` for the web app — the
EasyPrivacy list (uBlock, AdGuard, Brave, Safari blockers) drops every
browser request under ``/api/v1/metrics`` (see :mod:`catalog`).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.services import metric_overview

router = APIRouter(tags=["metrics"])


@router.get("/metrics/{key}/overview")
async def overview(
    key: str,
    principal: ReaderDep,
    session: SessionDep,
    days: Annotated[int, Query(ge=7, le=36500)] = 365,
) -> dict[str, Any]:
    """Latest reading, day value, averages, sources and daily series."""
    return await metric_overview.overview(session, principal.user.id, key, days)


@router.get("/catalog/{key}/overview")
async def catalog_overview(
    key: str,
    principal: ReaderDep,
    session: SessionDep,
    days: Annotated[int, Query(ge=7, le=36500)] = 365,
) -> dict[str, Any]:
    """Alias of ``/metrics/{key}/overview`` that blockers let through."""
    return await metric_overview.overview(session, principal.user.id, key, days)
