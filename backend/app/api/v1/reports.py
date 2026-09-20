"""Report generation endpoints (async job with sync fallback, §11)."""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from app.core.deps import PrincipalDep, SessionDep
from app.core.errors import NotFoundError
from app.models.report import Report
from app.schemas.export import ReportCreate, ReportOut
from app.services import audit
from app.services import reports as svc
from app.workers.queue import enqueue

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
async def create(
    body: ReportCreate, principal: PrincipalDep, session: SessionDep
) -> Report:
    """Queue a report; build it inline if no worker is available."""
    report = await svc.create_report(
        session,
        principal.user.id,
        type_=body.type,
        period_start=body.period_start,
        period_end=body.period_end,
        params=body.params,
    )
    await audit.record(
        session,
        action="report",
        entity="report",
        user_id=principal.user.id,
        entity_id=report.id,
    )
    await session.commit()
    if not await enqueue("generate_report", report.id):
        await svc.build(session, report)
        await session.commit()
    return report


@router.get("", response_model=list[ReportOut])
async def index(principal: PrincipalDep, session: SessionDep) -> list[Report]:
    """List the caller's recent reports."""
    return await svc.list_reports(session, principal.user.id)


@router.get("/{report_id}", response_model=ReportOut)
async def detail(
    report_id: str, principal: PrincipalDep, session: SessionDep
) -> Report:
    """Return a report's status and metadata."""
    return await svc.get_report(session, principal.user.id, report_id)


@router.get("/{report_id}/file")
async def download(
    report_id: str, principal: PrincipalDep, session: SessionDep
) -> FileResponse:
    """Stream a finished report file to its owner."""
    report = await svc.get_report(session, principal.user.id, report_id)
    if not report.file_path:
        raise NotFoundError("Report not ready")
    return FileResponse(report.file_path)
