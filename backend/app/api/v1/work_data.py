"""Work hours: statistics, export and import of past logs."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import Response

from app.core.deps import Principal, ReaderDep, SessionDep
from app.core.deps_query import require_scope_flex
from app.core.scopes import WRITE_MEASUREMENTS
from app.models.base import utcnow
from app.services import work, work_export, work_import, work_stats
from app.services.daily_rollup import user_zone
from app.services.timed_entries import local_day

router = APIRouter(prefix="/work", tags=["work"])

TapDep = Annotated[Principal, Depends(require_scope_flex(WRITE_MEASUREMENTS))]
Contract = Annotated[float, Query(gt=0, le=80)]


@router.get("/stats")
async def stats(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    contract_hours: Contract = 35.0,
) -> dict[str, Any]:
    """Totals, averages, overtime, weeks, months, 7/30/90/365 days."""
    first, last = await _period(session, principal.user.id, start, end)
    return await work_stats.stats(
        session, principal.user.id, first, last, contract_hours
    )


@router.get("/export")
async def export(
    principal: ReaderDep,
    session: SessionDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    level: Literal["sessions", "days", "weeks", "months"] = "days",
    file_format: Annotated[
        Literal["csv", "json", "xlsx"], Query(alias="format")
    ] = "csv",
    contract_hours: Contract = 35.0,
) -> Response:
    """Sessions, days, weeks or months as CSV, JSON or Excel."""
    user_id = principal.user.id
    first, last = await _period(session, user_id, start, end)
    data = await work_stats.stats(session, user_id, first, last, contract_hours)
    listed = await work.list_sessions(session, user_id, first, last)
    tz = await user_zone(session, user_id)
    table = work_export.rows(data, listed, level, tz)
    body, media = work_export.render(table, file_format)
    name = f"heures-travail-{level}-{first}-{last}.{file_format}"
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/import")
async def import_log(
    file: UploadFile,
    principal: TapDep,
    session: SessionDep,
    dry_run: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Import past clock-in / clock-out logs (txt, csv, json).

    ``dry_run=true`` only reads the file and shows what would be added.
    """
    data = await file.read()
    report = await work_import.import_file(
        session,
        principal.user.id,
        data,
        file.filename or "",
        dry_run=dry_run,
    )
    if not dry_run:
        await session.commit()
    return report


async def _period(
    session: SessionDep, user_id: str, start: date | None, end: date | None
) -> tuple[date, date]:
    """The asked days (default: the last 365 days)."""
    last = end or await local_day(session, user_id, utcnow())
    return start or last - timedelta(days=364), last
