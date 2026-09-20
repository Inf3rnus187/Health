"""Blocker-safe alias for the metric catalogue.

Some browser tracking/ad blockers drop any request whose path contains
"metrics" (treating it as telemetry), which breaks the SPA's catalogue
fetch. This exposes the same read at ``/catalog``; the canonical
``/metrics`` endpoints stay for API clients, scripts and the MCP server.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import PrincipalDep, SessionDep
from app.models.metric import MetricDefinition
from app.schemas.metric import MetricOut
from app.services import metrics as svc

router = APIRouter(tags=["metrics"])


@router.get("/catalog", response_model=list[MetricOut])
async def catalog(
    principal: PrincipalDep,
    session: SessionDep,
    domain: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
) -> list[MetricDefinition]:
    """Alias of ``GET /metrics`` (avoids client-side 'metrics' blockers)."""
    return await svc.list_metrics(
        session, domain=domain, source=source, active=active
    )
