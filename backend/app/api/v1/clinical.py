"""Clinical (CDA) endpoints: observation browser + document download."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import PrincipalDep, SessionDep
from app.models.health_raw import ClinicalDocument
from app.schemas.health_raw import (
    ClinicalDocOut,
    ObservationOut,
    ObservationPage,
)
from app.services import clinical as svc

router = APIRouter(prefix="/clinical", tags=["clinical"])


@router.get("/observations", response_model=ObservationPage)
async def observations(
    principal: PrincipalDep,
    session: SessionDep,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ObservationPage:
    """Return one page of clinical observations (searchable by label)."""
    rows, total = await svc.page(
        session, principal.user.id, search=search, limit=limit, offset=offset
    )
    return ObservationPage(
        items=[ObservationOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/document", response_model=ClinicalDocOut | None)
async def document(
    principal: PrincipalDep, session: SessionDep
) -> ClinicalDocument | None:
    """Return the stored CDA document summary, or null."""
    return await svc.document(session, principal.user.id)


@router.get("/document/file")
async def document_file(
    principal: PrincipalDep, session: SessionDep
) -> Response:
    """Download the raw CDA XML document."""
    data = await svc.document_bytes(session, principal.user.id)
    return Response(content=data, media_type="application/xml")
