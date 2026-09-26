"""The iPhone app's HealthKit sync: everything Health holds, incremental."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import Principal, SessionDep, require_scope
from app.core.scopes import WRITE_MEASUREMENTS
from app.schemas.healthkit import (
    HealthKitResult,
    HealthKitStatus,
    HealthKitSync,
)
from app.services import audit, healthkit_sync

router = APIRouter(prefix="/sync", tags=["sync"])

#: The app sends its token in the Authorization header (never the URL).
AppDep = Annotated[Principal, Depends(require_scope(WRITE_MEASUREMENTS))]


@router.post("/healthkit", response_model=HealthKitResult)
async def push(
    body: HealthKitSync, principal: AppDep, session: SessionDep
) -> HealthKitResult:
    """Store what the iPhone app read in HealthKit since its last sync.

    JSON: ``samples`` (5000 at most: ``uuid``, ``type``
    ``HKQuantityTypeIdentifier…``/``HKCategoryTypeIdentifier…``,
    ``start``, ``end``, ``value``, ``unit``, ``device``) — discrete
    quantities (HealthKit's own value and unit, 0.97 for 97 %) and
    categories (their ``HKCategoryValue…`` name; sleep: 0-5 or the name,
    with ``end``); ``statistics`` (5000: ``type``, ``start``, ``end``,
    ``sum``, ``unit``) — cumulative types (steps, distance, energy…) as
    ``HKStatisticsCollectionQuery`` sums, by hour; ``workouts`` (500:
    ``uuid``, ``activity``, ``start``, ``end``, ``duration_min``,
    ``energy_kcal``, ``distance_km``); ``deleted`` (5000 UUIDs). Dates
    ISO 8601 (without offset: local). A UUID sent again replaces itself;
    sums replace those they overlap. A cumulative type sent as samples,
    a discrete one as statistics, an unknown type or value is refused
    and counted in ``skipped`` (``type``, ``reason``, ``count``), never
    fatal. The touched days are recomputed (``days``). Token scope
    ``write:measurements``, in the ``Authorization`` header only.
    """
    result = await healthkit_sync.sync(session, principal.user.id, body)
    await audit.record(
        session,
        action="sync",
        entity="healthkit",
        user_id=principal.user.id,
        source="app" if principal.token_id else "web",
        payload={k: v for k, v in result.items() if k != "skipped"},
    )
    await session.commit()
    return HealthKitResult(**result)


@router.get("/healthkit", response_model=HealthKitStatus)
async def state(principal: AppDep, session: SessionDep) -> HealthKitStatus:
    """What the hub holds from the app (to resume after a reinstall).

    ``last_sync_at``, ``samples``, ``workouts``, and per metric ``key``,
    ``label``, ``samples``, ``last`` (newest sample start). Same token.
    """
    return HealthKitStatus(
        **await healthkit_sync.status(session, principal.user.id)
    )
