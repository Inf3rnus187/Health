"""Paginated raw-sample browser (survives millions of rows)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import PrincipalDep, SessionDep
from app.schemas.health_raw import SampleOut, SamplePage
from app.services import samples as svc

router = APIRouter(prefix="/samples", tags=["samples"])


@router.get("", response_model=SamplePage)
async def index(
    principal: PrincipalDep,
    session: SessionDep,
    metric_key: Annotated[str | None, Query()] = None,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SamplePage:
    """Return one filtered page of raw samples plus the total count."""
    rows, total = await svc.page(
        session,
        principal.user.id,
        metric_key=metric_key,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
    )
    return SamplePage(
        items=[SampleOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
