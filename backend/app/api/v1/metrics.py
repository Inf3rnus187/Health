"""Dynamic metric-registry endpoints (add a field with no migration)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.deps import PrincipalDep, SessionDep
from app.core.deps_admin import CatalogDep
from app.models.metric import MetricDefinition
from app.schemas.metric import MetricCreate, MetricOut, MetricUpdate
from app.services import audit
from app.services import metrics as svc

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricOut])
async def index(
    principal: PrincipalDep,
    session: SessionDep,
    domain: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
) -> list[MetricDefinition]:
    """List metric definitions, filterable by domain/source/active."""
    return await svc.list_metrics(
        session, domain=domain, source=source, active=active
    )


@router.post("", response_model=MetricOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: MetricCreate, principal: CatalogDep, session: SessionDep
) -> MetricDefinition:
    """Register a new metric at runtime (administrator: shared catalogue)."""
    metric = await svc.create_metric(session, principal.user.id, body)
    await audit.record(
        session,
        action="create",
        entity="metric",
        user_id=principal.user.id,
        entity_id=metric.id,
    )
    await session.commit()
    return metric


@router.get("/{key}", response_model=MetricOut)
async def detail(
    key: str, principal: PrincipalDep, session: SessionDep
) -> MetricDefinition:
    """Return one metric definition by key."""
    return await svc.get_metric(session, key)


@router.patch("/{key}", response_model=MetricOut)
async def update(
    key: str,
    body: MetricUpdate,
    principal: CatalogDep,
    session: SessionDep,
) -> MetricDefinition:
    """Update a metric's label, bounds, options or active flag.

    Administrator only: the catalogue is shared by every user.
    """
    metric = await svc.update_metric(session, key, body)
    await audit.record(
        session,
        action="update",
        entity="metric",
        user_id=principal.user.id,
        entity_id=metric.id,
    )
    await session.commit()
    return metric
