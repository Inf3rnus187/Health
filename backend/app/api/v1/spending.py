"""What meals paid for cost: Uber Eats and other deliveries, receipts."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.core.deps import ReaderDep, SessionDep
from app.core.errors import InvalidInputError
from app.models.base import utcnow
from app.services import spending
from app.services.timed_entries import local_day

router = APIRouter(prefix="/spending", tags=["work-file"])


@router.get("/meals")
async def meals(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    kind: Annotated[str, Query(pattern="^(livraison|repas|tout)$")] = (
        "livraison"
    ),
    bucket: Annotated[str, Query(pattern="^(auto|day|week|month)$")] = "auto",
) -> dict[str, Any]:
    """Spending on meals paid for over ``start``..``end``.

    ``kind``: ``livraison`` (Uber Eats and other deliveries, default),
    ``repas`` (receipts, restaurants) or ``tout``. Answers the total, the
    orders, the average basket, the largest order, the monthly average,
    the late orders (21:00 – 05:00), the spending per ``bucket`` (day,
    week, month; ``auto`` from the span, empty periods included), per
    hour of the day, and the establishments that cost the most. Without
    ``start``: from the first order; without ``end``: up to today.
    """
    user_id = principal.user.id
    last = end or await local_day(session, user_id, utcnow())
    if start is not None and start > last:
        raise InvalidInputError("start is after end")
    return await spending.meals(session, user_id, (start, last), kind, bucket)
