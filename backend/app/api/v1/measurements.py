"""Measurement endpoints: idempotent batch write and reads."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.constants import AGGREGATIONS
from app.core.deps import Principal, ReaderDep, SessionDep, require_scope
from app.core.errors import InvalidInputError
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.measurement import Measurement
from app.schemas.common import Message
from app.schemas.measurement import (
    DeleteResult,
    IdList,
    MeasurementBatch,
    MeasurementOut,
    Series,
    SeriesPoint,
)
from app.services import audit, overwrites
from app.services import measurements as svc

router = APIRouter(prefix="/measurements", tags=["measurements"])

WriteDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post(
    "",
    response_model=list[MeasurementOut],
    status_code=status.HTTP_201_CREATED,
)
async def create(
    body: MeasurementBatch, principal: WriteDep, session: SessionDep
) -> list[Measurement]:
    """Record one or more measurements (idempotent, batch).

    A day's value is **replaced**, not added to: use ``/sync/tally`` to
    add to a count. The values replaced are kept in the audit log.
    """
    is_user = principal.source == "jwt"
    previous = await overwrites.replaced(session, principal.user.id, body.items)
    rows = await svc.record_batch(
        session,
        principal.user.id,
        body.items,
        source="manual" if is_user else "script",
        token_id=principal.token_id,
    )
    await audit.record(
        session,
        action="record",
        entity="measurement",
        user_id=principal.user.id,
        source="api" if is_user else "token",
        payload={"count": len(rows), "replaced": previous},
    )
    await session.commit()
    return rows


@router.get("/series", response_model=Series)
async def series(
    principal: ReaderDep,
    session: SessionDep,
    metric_key: Annotated[str, Query()],
    agg: Annotated[str, Query()] = "avg",
    window: Annotated[int, Query(ge=1, le=365)] = 7,
) -> Series:
    """Return a rolling-aggregated series for a numeric metric."""
    if agg not in AGGREGATIONS:
        raise InvalidInputError(f"invalid agg: {agg}")
    points = await svc.aggregate(
        session, principal.user.id, metric_key, agg, window
    )
    return Series(
        metric_key=metric_key,
        agg=agg,
        window_days=window,
        points=[SeriesPoint(date_key=d, value=v) for d, v in points],
    )


@router.get("", response_model=list[MeasurementOut])
async def index(
    principal: ReaderDep,
    session: SessionDep,
    metric_key: Annotated[str | None, Query()] = None,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    event_id: Annotated[str | None, Query()] = None,
) -> list[Measurement]:
    """Return raw measurements matching the given filters."""
    return await svc.query(
        session,
        principal.user.id,
        metric_key=metric_key,
        start=start,
        end=end,
        event_id=event_id,
    )


@router.delete("/{measurement_id}", response_model=Message)
async def delete(
    measurement_id: str, principal: WriteDep, session: SessionDep
) -> Message:
    """Delete one measurement (owner-scoped)."""
    await svc.delete_one(session, principal.user.id, measurement_id)
    await audit.record(
        session,
        action="delete",
        entity="measurement",
        user_id=principal.user.id,
        entity_id=measurement_id,
    )
    await session.commit()
    return Message(detail="deleted")


@router.post("/delete", response_model=DeleteResult)
async def delete_bulk(
    body: IdList, principal: WriteDep, session: SessionDep
) -> DeleteResult:
    """Delete several measurements at once (owner-scoped)."""
    count = await svc.delete_many(session, principal.user.id, body.ids)
    await audit.record(
        session,
        action="delete",
        entity="measurement",
        user_id=principal.user.id,
        payload={"deleted": count},
    )
    await session.commit()
    return DeleteResult(deleted=count)
