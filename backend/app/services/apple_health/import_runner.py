"""Drive one import: reset prior data, load XML, then ECG and routes.

Accepts either a ``.zip`` archive (export.xml + electrocardiograms +
workout-routes) or a bare ``export.xml``. Progress is written back onto
the :class:`ImportJob` as the streaming pass advances.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utcnow
from app.models.health_raw import (
    EcgRecord,
    HealthSample,
    ImportJob,
    RouteFile,
    Workout,
)
from app.services.apple_health import blobs
from app.services.apple_health.importer import Progress, run_import


async def process(session: AsyncSession, job: ImportJob) -> None:
    """Replace prior Apple data, then import the file behind ``job``."""
    await reset(session, job.user_id)
    path = Path(job.file_path)
    if zipfile.is_zipfile(path):
        await _process_zip(session, job, path)
    else:
        await _process_xml_file(session, job, path)


async def _process_zip(
    session: AsyncSession, job: ImportJob, path: Path
) -> None:
    """Import export.xml, ECG traces and routes from a zip archive."""
    with zipfile.ZipFile(path) as archive:
        await _import_xml(session, job, archive)
        await _import_blobs(session, job, archive)


async def _process_xml_file(
    session: AsyncSession, job: ImportJob, path: Path
) -> None:
    """Import a bare export.xml file."""
    with path.open("rb") as stream:
        stats = await run_import(
            session, job.user_id, stream, _progress(session, job)
        )
    job.samples, job.workouts = stats.samples, stats.workouts
    await session.commit()


async def _import_xml(
    session: AsyncSession, job: ImportJob, archive: zipfile.ZipFile
) -> None:
    """Stream export.xml out of the archive into raw storage."""
    name = _find_member(archive, "/export.xml")
    if name is None:
        return
    with archive.open(name) as stream:
        stats = await run_import(
            session, job.user_id, stream, _progress(session, job)
        )
    job.samples, job.workouts = stats.samples, stats.workouts
    await session.commit()


async def _import_blobs(
    session: AsyncSession, job: ImportJob, archive: zipfile.ZipFile
) -> None:
    """Store every ECG CSV and GPX route found in the archive."""
    job.phase = "files"
    for name in archive.namelist():
        low = name.lower()
        if low.endswith(".csv") and "electrocardiogram" in low:
            _add_ecg(session, job, archive.read(name))
        elif low.endswith(".gpx"):
            _add_route(session, job, archive.read(name))
    await session.commit()


def _add_ecg(session: AsyncSession, job: ImportJob, data: bytes) -> None:
    """Persist one ECG record."""
    meta = blobs.save_ecg(job.user_id, data)
    session.add(EcgRecord(user_id=job.user_id, **meta))
    job.ecg += 1


def _add_route(session: AsyncSession, job: ImportJob, data: bytes) -> None:
    """Persist one GPS route."""
    meta = blobs.save_route(job.user_id, data)
    session.add(RouteFile(user_id=job.user_id, **meta))
    job.routes += 1


def _find_member(archive: zipfile.ZipFile, suffix: str) -> str | None:
    """Return the first archive member whose name ends with ``suffix``."""
    for name in archive.namelist():
        if name.endswith(suffix) or name == suffix.lstrip("/"):
            return name
    return None


def _progress(session: AsyncSession, job: ImportJob) -> Progress:
    """Build a callback that records parse progress on the job."""

    async def update(processed: int) -> None:
        job.processed = processed
        job.phase = "parsing"
        job.updated_at = utcnow()
        await session.commit()

    return update


async def reset(session: AsyncSession, user_id: str) -> None:
    """Delete prior Apple-sourced rows so a re-import is idempotent."""
    await _unlink_blobs(session, user_id)
    for model in (HealthSample, Workout, EcgRecord, RouteFile):
        await session.execute(
            sql_delete(model).where(
                model.user_id == user_id, model.source == "apple"
            )
        )
    await session.commit()


async def _unlink_blobs(session: AsyncSession, user_id: str) -> None:
    """Remove ECG/route files on disk before their rows are deleted."""
    paths: list[str] = []
    for model in (EcgRecord, RouteFile):
        rows = await session.execute(
            select(model.file_path).where(
                model.user_id == user_id, model.source == "apple"
            )
        )
        paths.extend(row[0] for row in rows)
    for path in paths:
        Path(path).unlink(missing_ok=True)
