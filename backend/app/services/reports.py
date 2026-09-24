"""Report creation, retrieval and building (§11)."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.metric import MetricDefinition
from app.models.report import Report
from app.services import appointments as appts_svc
from app.services import (
    audit,
    clinical_facts,
    clinical_synthesis,
    export,
    export_formats,
    report_extra,
    reports_pdf,
    work_health_report,
    work_pdf,
    work_stats,
)
from app.services import conditions as cond_svc
from app.services import medical as med_svc
from app.services import treatments as treat_svc
from app.services.timed_entries import local_day

_STATUS_FR = {
    "active": "active",
    "resolved": "résolue",
    "suspected": "suspectée",
}
_KIND_FR = {
    "ordonnance": "Ordonnance",
    "imagerie": "Imagerie",
    "compte_rendu": "Compte-rendu",
    "biologie": "Biologie",
    "efr": "EFR",
    "test_marche": "Test de marche",
    "cda": "CDA",
    "vaccination": "Vaccination",
    "autre": "Autre",
}

_settings = get_settings()
_PDF = {"clinical_pdf", "synthesis"}
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
    """Generate the report file and mark it ready (or error).

    The file's SHA-256 is kept on the report and in the audit log: a copy
    handed to a doctor or a court can be checked (``/reports/verify``).
    """
    try:
        data, ext = await _data(session, report)
        report.file_path = str(_write(report, ext, data))
        report.sha256 = hashlib.sha256(data).hexdigest()
        report.status = "ready"
        await audit.record(
            session,
            action="generate",
            entity="report",
            user_id=report.user_id,
            entity_id=report.id,
            payload={"sha256": report.sha256, "type": report.type},
        )
    except Exception as exc:  # noqa: BLE001
        report.status = "error"
        _log.warning("report_failed", report_id=report.id, error=str(exc))


async def verify(
    session: AsyncSession, user_id: str, data: bytes
) -> dict[str, Any]:
    """Whether ``data`` is one of the user's reports, byte for byte."""
    digest = hashlib.sha256(data).hexdigest()
    found = await session.scalar(
        select(Report).where(Report.user_id == user_id, Report.sha256 == digest)
    )
    return {"sha256": digest, "authentic": found is not None, "report": found}


async def _data(session: AsyncSession, report: Report) -> tuple[bytes, str]:
    """The report's bytes and file extension."""
    if report.type == "work":
        return await _work(session, report), "pdf"
    if report.type == "work_health":
        period = (report.period_start, report.period_end)
        data = await work_health_report.render(
            session, report.user_id, period, _contract(report)
        )
        return data, "pdf"
    return await _health(session, report)


async def _health(session: AsyncSession, report: Report) -> tuple[bytes, str]:
    """A health report or export over the period."""
    rows = await export.tidy_rows(
        session,
        report.user_id,
        start=report.period_start,
        end=report.period_end,
    )
    meta = await _metric_meta(session, {r["metric_key"] for r in rows})
    span = await _span(session, report, rows)
    care = await _care(session, report.user_id, span)
    if report.type == "synthesis":
        facts = await clinical_facts.gather(session, report.user_id)
        report.summary = await clinical_synthesis.synthesize(facts)
    extra = None
    if report.type in _PDF:
        extra = await report_extra.gather(session, report, rows, span)
    return _render(report, rows, meta, care, extra)


async def _span(
    session: AsyncSession, report: Report, rows: list[dict[str, Any]]
) -> tuple[date, date]:
    """The report's days: asked, else from the first value up to today."""
    end = report.period_end or await local_day(
        session, report.user_id, utcnow()
    )
    first = date.fromisoformat(rows[0]["date"]) if rows else end
    return report.period_start or min(first, end), end


async def _work(session: AsyncSession, report: Report) -> bytes:
    """The work-hours report (default: every session, 35 h contract)."""
    last = report.period_end or date.today()
    known = await work_health_report.first_day(session, report.user_id)
    first = report.period_start or known or last - timedelta(days=364)
    contract = _contract(report)
    stats = await work_stats.stats(
        session, report.user_id, first, last, contract
    )
    return work_pdf.work_pdf(stats)


def _contract(report: Report) -> float:
    """The weekly contract hours asked for the report (35 by default)."""
    return float((report.params or {}).get("contract_hours") or 35)


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
    report: Report,
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    care: dict[str, list[str]],
    extra: dict[str, Any] | None,
) -> tuple[bytes, str]:
    """Render the report body and its file extension."""
    if report.type in _PDF:
        pdf = reports_pdf.clinical_pdf(
            report, rows, meta, care, report.summary, extra
        )
        return pdf, "pdf"
    data, _media, ext = export_formats.render(report.type, rows, report.user_id)
    return data, ext


async def _care(
    session: AsyncSession, user_id: str, span: tuple[date, date]
) -> dict[str, list[str]]:
    """The care record as printable lines (appointments of the period)."""
    conds = await cond_svc.list_all(session, user_id)
    treats = await treat_svc.list_all(session, user_id)
    appts = await appts_svc.list_all(session, user_id)
    inside = [a for a in appts if span[0] <= a.starts_at.date() <= span[1]]
    docs = await med_svc.list_documents(session, user_id)
    return {
        "Maladies": [_cond(c) for c in conds],
        "Traitements": [_treat(t) for t in treats],
        "Rendez-vous de la période": [_appt(a) for a in inside],
        "Documents médicaux (30 plus récents)": [_doc(d) for d in docs[:30]],
    }


def _cond(cond: Any) -> str:
    """Format one condition line."""
    status = _STATUS_FR.get(cond.status, cond.status)
    code = f" [{cond.code}]" if cond.code else ""
    return f"{cond.name} ({status}){code}"


def _treat(treat: Any) -> str:
    """Format one treatment line: dose, frequency, doses a day, dates."""
    per_day = f"{treat.doses_per_day}/jour" if treat.doses_per_day else ""
    desc = " · ".join(p for p in (treat.dose, treat.frequency, per_day) if p)
    state = "actif" if treat.active else "arrêté"
    body = f" — {desc}" if desc else ""
    dates = f" ({treat.start_date or '?'} -> {treat.end_date or '…'})"
    shown = dates if treat.start_date or treat.end_date else ""
    return f"{treat.name}{body}{shown} [{state}]"


def _appt(appt: Any) -> str:
    """Format one appointment line (with the practitioner)."""
    who = f" — {appt.practitioner}" if appt.practitioner else ""
    where = f" — {appt.location}" if appt.location else ""
    return f"{appt.starts_at.date()} — {appt.title}{who}{where}"


def _doc(doc: Any) -> str:
    """Format one document index line."""
    day = doc.doc_date or doc.created_at.date()
    return f"{day} — {doc.title} [{_KIND_FR.get(doc.kind, doc.kind)}]"


def _write(report: Report, ext: str, data: bytes) -> Path:
    """Write the report bytes under the exports directory."""
    base = Path(_settings.exports_dir) / report.user_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{report.id}.{ext}"
    path.write_bytes(data)
    return path
