"""ARQ worker entrypoint.

Ships with a single ``ping`` job so the worker has something to run;
photo-analysis and report jobs are registered here from Phase 4 onward.
"""

from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.workers.jobs import analyze_document, reconcile_data

_log = get_logger("worker")


async def ping(ctx: dict[str, Any]) -> str:
    """Trivial job used for liveness checks."""
    return "pong"


async def analyze_photo(ctx: dict[str, Any], photo_id: str) -> str:
    """Run the photo pipeline for ``photo_id`` in a fresh session."""
    from app.core.db import SessionFactory
    from app.services.photo_pipeline import process

    async with SessionFactory() as session:
        await process(session, photo_id)
    return photo_id


async def import_apple_health_job(ctx: dict[str, Any], job_id: str) -> str:
    """Run a queued Apple Health import in a fresh session."""
    from app.core.db import SessionFactory
    from app.services import imports

    async with SessionFactory() as session:
        await imports.run_job(session, job_id)
    return job_id


async def generate_report(ctx: dict[str, Any], report_id: str) -> str:
    """Build the report ``report_id`` in a fresh session."""
    from app.core.db import SessionFactory
    from app.models.report import Report
    from app.services import reports

    async with SessionFactory() as session:
        report = await session.get(Report, report_id)
        if report is not None:
            await reports.build(session, report)
            await session.commit()
    return report_id


async def _startup(ctx: dict[str, Any]) -> None:
    """Configure logging when the worker boots."""
    configure_logging()
    _log.info("worker_started")
    await _resume_documents()


async def _resume_documents() -> None:
    """Re-queue document readings a previous worker left unfinished."""
    from app.core.db import SessionFactory
    from app.services import document_ai

    try:
        async with SessionFactory() as session:
            resumed = await document_ai.requeue_stale(session)
    except Exception as exc:  # noqa: BLE001 - never block the worker boot
        _log.warning("resume_documents_failed", error=str(exc))
        return
    _log.info("documents_resumed", count=resumed)


class WorkerSettings:
    """ARQ worker configuration read by ``arq app...WorkerSettings``."""

    functions = [
        ping,
        analyze_photo,
        analyze_document,
        reconcile_data,
        generate_report,
        import_apple_health_job,
    ]
    on_startup = _startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    # Full-history imports can run for many minutes; give them room.
    job_timeout = 7200
    max_tries = 1
