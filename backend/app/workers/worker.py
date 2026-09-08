"""ARQ worker entrypoint.

Ships with a single ``ping`` job so the worker has something to run;
photo-analysis and report jobs are registered here from Phase 4 onward.
"""

from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

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


class WorkerSettings:
    """ARQ worker configuration read by ``arq app...WorkerSettings``."""

    functions = [ping, analyze_photo, generate_report]
    on_startup = _startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
