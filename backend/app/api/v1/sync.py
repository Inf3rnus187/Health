"""One-tap mobile sync: a pre-filled Shortcut + flat health ingest."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.deps import (
    InteractiveDep,
    Principal,
    SessionDep,
    require_scope,
)
from app.core.deps_query import require_scope_flex
from app.core.scopes import INGEST_WATCH, WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.schemas.ingest import (
    HealthSyncPayload,
    IngestPayload,
    IngestResult,
    IngestSample,
    TallyPayload,
    TallyResult,
)
from app.services import (
    audit,
    auto_export,
    ingest,
    shortcut,
    tally,
    timed_entries,
)
from app.services import tokens as tokens_svc

router = APIRouter(prefix="/sync", tags=["sync"])

WatchDep = Annotated[Principal, Depends(require_scope(INGEST_WATCH))]
FlexWriteDep = Annotated[
    Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))
]

_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


@router.get("/shortcut")
async def download_shortcut(
    principal: InteractiveDep,
    session: SessionDep,
    base: Annotated[str, Query()] = "",
) -> Response:
    """Mint an ingest token and return a pre-filled ``.shortcut``."""
    token, secret = await tokens_svc.create_token(
        session, principal.user, "iPhone (Raccourci)", [INGEST_WATCH], None
    )
    await audit.record(
        session,
        action="create",
        entity="sync_shortcut",
        user_id=principal.user.id,
        entity_id=token.id,
    )
    await session.commit()
    data = shortcut.build_shortcut(_endpoint(base), secret)
    disposition = 'attachment; filename="Phoenix Sante.shortcut"'
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": disposition},
    )


@router.post("/health", response_model=IngestResult)
async def sync_health(
    body: HealthSyncPayload, principal: WatchDep, session: SessionDep
) -> IngestResult:
    """Ingest a flat ``{healthkit_type: value}`` map (Shortcut-friendly)."""
    ok, bad = _samples(body.metrics)
    if not ok:
        return IngestResult(recorded=0, skipped=bad)
    day = body.date_key or date.today()
    payload = IngestPayload(date_key=day, samples=ok)
    result = await ingest.ingest(
        session,
        principal.user.id,
        "watch",
        payload,
        token_id=principal.token_id,
    )
    await session.commit()
    return IngestResult(recorded=result.recorded, skipped=result.skipped + bad)


@router.post("/tally", response_model=TallyResult)
async def tally_counter(
    body: TallyPayload, principal: FlexWriteDep, session: SessionDep
) -> TallyResult:
    """Add to a daily counter (café, cigarette, bouteille d'eau).

    Never erases the day's total; a negative amount takes back a wrong
    entry. Each step is audited with the day's total before and after.
    """
    user_id = principal.user.id
    day = body.date_key or await timed_entries.local_day(
        session, user_id, utcnow()
    )
    step = await tally.increment(
        session,
        user_id,
        body.metric,
        body.amount,
        day,
        token_id=principal.token_id,
    )
    await session.commit()
    return TallyResult(
        metric=body.metric,
        date_key=day,
        previous=step.previous,
        total=step.total,
        detail=step.detail,
    )


@router.post("/auto-export", response_model=IngestResult)
async def auto_export_ingest(
    body: dict[str, Any], principal: FlexWriteDep, session: SessionDep
) -> IngestResult:
    """Ingest a Health Auto Export JSON payload (JSON body, no file)."""
    result = await auto_export.ingest(
        session, principal.user.id, body, token_id=principal.token_id
    )
    await session.commit()
    return result


def _endpoint(base: str) -> str:
    """Build the absolute /sync/health URL from the caller's origin."""
    root = base.rstrip("/") if base.startswith("http") else ""
    return f"{root}/api/v1/sync/health"


def _samples(
    metrics: dict[str, Any],
) -> tuple[list[IngestSample], list[str]]:
    """Split a flat metric map into valid samples and unparsable keys."""
    ok: list[IngestSample] = []
    bad: list[str] = []
    for hk, raw in metrics.items():
        num = _num(raw)
        if num is None:
            bad.append(hk)
            continue
        ok.append(IngestSample(healthkit_type=hk, value=num))
    return ok, bad


def _num(value: Any) -> float | None:
    """Leniently coerce a value to float (handles ``"8 542 pas"``)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = re.sub(r"[\s  ]", "", str(value))
    match = _NUM.search(text)
    if match is None:
        return None
    return float(match.group().replace(",", "."))
