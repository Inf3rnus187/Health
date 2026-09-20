"""Report creation, retrieval and building (§11)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.metric import MetricDefinition
from app.models.report import Report
from app.services import export, export_formats, reports_pdf

_settings = get_settings()
_log = get_logger("reports")


async def create_report(
    session: AsyncSession,
    user_id: str,
    *,
    type_: str,
    period_start: date | None,
    period_end: date | None,
    params: dict[str, Any] | None,
) -> Report:
    """Create a pending report row."""
    report = Report(
        user_id=user_id,
        type=type_,
        period_start=period_start,
        period_end=period_end,
        params=params or {},
        status="pending",
    )
    session.add(report)
    await session.flush()
    return report


async def get_report(
    session: AsyncSession, user_id: str, report_id: str
) -> Report:
    """Return one of the user's reports or raise :class:`NotFoundError`."""
    report = await session.get(Report, report_id)
    if report is None or report.user_id != user_id:
        raise NotFoundError("Report not found")
    return report


async def list_reports(session: AsyncSession, user_id: str) -> list[Report]:
    """Return the user's recent reports, newest first."""
    result = await session.execute(
        select(Report)
        .where(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def build(session: AsyncSession, report: Report) -> None:
    """Generate the report file and mark it ready (or error)."""
    try:
        rows = await export.tidy_rows(
            session,
            report.user_id,
            start=report.period_start,
            end=report.period_end,
        )
        meta = await _metric_meta(session, {r["metric_key"] for r in rows})
        data, ext = _render(report, rows, meta)
        report.file_path = str(_write(report, ext, data))
        report.status = "ready"
    except Exception as exc:  # noqa: BLE001
        report.status = "error"
        _log.warning("report_failed", report_id=report.id, error=str(exc))


async def _metric_meta(session: AsyncSession, keys: set[str]) -> dict[str, Any]:
    """Return ``key -> {label, domain, unit}`` for the referenced metrics."""
    if not keys:
        return {}
    result = await session.execute(
        select(MetricDefinition).where(MetricDefinition.key.in_(keys))
    )
    return {
        m.key: {"label": m.label, "domain": m.domain, "unit": m.unit}
        for m in result.scalars()
    }


def _render(
    report: Report, rows: list[dict[str, Any]], meta: dict[str, Any]
) -> tuple[bytes, str]:
    """Render the report body and its file extension."""
    if report.type == "clinical_pdf":
        return reports_pdf.clinical_pdf(report, rows, meta), "pdf"
    data, _media, ext = export_formats.render(report.type, rows, report.user_id)
    return data, ext


def _write(report: Report, ext: str, data: bytes) -> Path:
    """Write the report bytes under the exports directory."""
    base = Path(_settings.exports_dir) / report.user_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{report.id}.{ext}"
    path.write_bytes(data)
    return path
