"""Ingestion endpoints: Apple Watch, CPAP, and mapping management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import (
    Principal,
    PrincipalDep,
    SessionDep,
    UserDep,
    require_scope,
)
from app.core.scopes import INGEST_PPC, INGEST_WATCH
from app.models.mapping import IngestMapping
from app.schemas.ingest import (
    IngestPayload,
    IngestResult,
    MappingCreate,
    MappingOut,
)
from app.services import audit, ingest
from app.services import mappings as mapping_svc

router = APIRouter(prefix="/ingest", tags=["ingest"])

WatchDep = Annotated[Principal, Depends(require_scope(INGEST_WATCH))]
PpcDep = Annotated[Principal, Depends(require_scope(INGEST_PPC))]


async def _run(
    session: SessionDep, principal: Principal, source: str, body: IngestPayload
) -> IngestResult:
    """Ingest a payload for one source and audit the outcome."""
    result = await ingest.ingest(
        session, principal.user.id, source, body, token_id=principal.token_id
    )
    await audit.record(
        session,
        action="ingest",
        entity=source,
        user_id=principal.user.id,
        source="token" if principal.source == "token" else "api",
        payload={"recorded": result.recorded, "skipped": len(result.skipped)},
    )
    await session.commit()
    return result


@router.post("/watch", response_model=IngestResult)
async def watch(
    body: IngestPayload, principal: WatchDep, session: SessionDep
) -> IngestResult:
    """Ingest Apple Watch / HealthKit samples (night + previous day)."""
    return await _run(session, principal, "watch", body)


@router.post("/ppc", response_model=IngestResult)
async def ppc(
    body: IngestPayload, principal: PpcDep, session: SessionDep
) -> IngestResult:
    """Ingest CPAP machine data (hours, AHI, leaks, pressure)."""
    return await _run(session, principal, "ppc", body)


@router.get("/mappings", response_model=list[MappingOut])
async def mappings_index(
    principal: PrincipalDep, session: SessionDep
) -> list[IngestMapping]:
    """List the caller's mappings plus the global defaults."""
    return await mapping_svc.list_mappings(session, principal.user.id)


@router.post(
    "/mappings",
    response_model=MappingOut,
    status_code=status.HTTP_201_CREATED,
)
async def mappings_create(
    body: MappingCreate, principal: UserDep, session: SessionDep
) -> IngestMapping:
    """Add or override an external-key → metric-key mapping."""
    mapping = await mapping_svc.create_mapping(session, principal.user.id, body)
    await session.commit()
    return mapping
