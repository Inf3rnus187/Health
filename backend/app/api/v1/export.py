"""Raw data export endpoint (CSV/JSON/XLSX/FHIR, §11)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import PrincipalDep, SessionDep
from app.services import export as svc
from app.services import export_formats

router = APIRouter(tags=["exports"])


@router.get("/export")
async def export_data(
    principal: PrincipalDep,
    session: SessionDep,
    fmt: Annotated[str, Query(alias="format")] = "csv",
    domain: Annotated[str | None, Query()] = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> Response:
    """Stream a tidy export in the requested format."""
    rows = await svc.tidy_rows(
        session, principal.user.id, domain=domain, start=start, end=end
    )
    data, media, ext = export_formats.render(fmt, rows, principal.user.id)
    disposition = f'attachment; filename="phoenix_export.{ext}"'
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": disposition},
    )
