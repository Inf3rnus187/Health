"""Import-job lifecycle: create, run in background, query status."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.base import utcnow
from app.models.health_raw import ImportJob
from app.services.apple_health.import_runner import process
from app.workers.queue import enqueue


async def create_job(
    session: AsyncSession, user_id: str, filename: str, file_path: str
) -> ImportJob:
    """Record a queued import job for a stored upload."""
    job = ImportJob(user_id=user_id, filename=filename, file_path=file_path)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def run_job(session: AsyncSession, job_id: str) -> None:
    """Execute an import job, recording progress and final status."""
    job = await session.get(ImportJob, job_id)
    if job is None:
        return
    job.status, job.updated_at = "running", utcnow()
    await session.commit()
    try:
        await process(session, job)
    except Exception as exc:  # noqa: BLE001
        await _fail(session, job_id, str(exc))
        return
    job.status, job.phase, job.updated_at = "done", "done", utcnow()
    await session.commit()
    # One truth: merge duplicate keys, rebuild daily values from raw data.
    await enqueue("reconcile_data", job.user_id)


async def get_job(
    session: AsyncSession, user_id: str, job_id: str
) -> ImportJob:
    """Return one job owned by the user or raise NotFound."""
    job = await session.get(ImportJob, job_id)
    if job is None or job.user_id != user_id:
        raise NotFoundError("Import job not found")
    return job


async def list_jobs(session: AsyncSession, user_id: str) -> list[ImportJob]:
    """Return the user's most recent import jobs."""
    result = await session.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user_id)
        .order_by(ImportJob.created_at.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def _fail(session: AsyncSession, job_id: str, message: str) -> None:
    """Mark a job as failed after rolling back a partial transaction."""
    await session.rollback()
    job = await session.get(ImportJob, job_id)
    if job is None:
        return
    job.status, job.phase = "error", "error"
    job.error, job.updated_at = message[:500], utcnow()
    await session.commit()
