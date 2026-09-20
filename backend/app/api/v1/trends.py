"""Calendar-bucketed trend endpoint (day/week/month/year)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import PrincipalDep, SessionDep
from app.core.errors import InvalidInputError
from app.schemas.measurement import SeriesPoint, TrendOut
from app.services import trends as svc

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("", response_model=TrendOut)
async def index(
    principal: PrincipalDep,
    session: SessionDep,
    metric_key: Annotated[str, Query()],
    bucket: Annotated[str, Query()] = "day",
) -> TrendOut:
    """Return a metric's values bucketed by the given period."""
    if bucket not in svc.BUCKETS:
        raise InvalidInputError(f"invalid bucket: {bucket}")
    points = await svc.trend(session, principal.user.id, metric_key, bucket)
    return TrendOut(
        metric_key=metric_key,
        bucket=bucket,
        points=[SeriesPoint(date_key=day, value=val) for day, val in points],
    )
