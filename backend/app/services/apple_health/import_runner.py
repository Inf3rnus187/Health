"""Drive one import: reset prior data, load XML, then ECG and routes.

Accepts either a ``.zip`` archive (export.xml + electrocardiograms +
workout-routes) or a bare ``export.xml``. Progress is written back onto
the :class:`ImportJob` as the streaming pass advances.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import new_uuid, utcnow
from app.models.health_raw import (
    ClinicalDocument,
    ClinicalObservation,
    EcgRecord,
    HealthSample,
    ImportJob,
    RouteFile,
    Workout,
)
from app.services.apple_health import blobs
from app.services.apple_health.cda import Observation, iter_observations
from app.services.apple_health.importer import Progress, run_import

_OBS_BATCH = 1000


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
        await _import_cda(session, job, archive)


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
    """Persist one ECG record, skipping poor-quality recordings."""
    meta = blobs.save_ecg(job.user_id, data)
    if meta is None:
        return
    session.add(EcgRecord(user_id=job.user_id, **meta))
    job.ecg += 1


def _add_route(session: AsyncSession, job: ImportJob, data: bytes) -> None:
    """Persist one GPS route."""
    meta = blobs.save_route(job.user_id, data)
    session.add(RouteFile(user_id=job.user_id, **meta))
    job.routes += 1


async def _import_cda(
    session: AsyncSession, job: ImportJob, archive: zipfile.ZipFile
) -> None:
    """Store the CDA file and its parsed observations, if present."""
    name = _find_member(archive, "export_cda.xml")
    if name is None:
        return
    job.phase = "clinical"
    await session.commit()
    data = archive.read(name)
    path = blobs.save_cda(job.user_id, data)
    count = await _store_observations(session, job.user_id, data)
    session.add(
        ClinicalDocument(
            user_id=job.user_id, file_path=path, observation_count=count
        )
    )
    await session.commit()


async def _store_observations(
    session: AsyncSession, user_id: str, data: bytes
) -> int:
    """Bulk-insert every value-bearing CDA observation."""
    rows: list[dict[str, Any]] = []
    total = 0
    for obs in iter_observations(io.BytesIO(data)):
        rows.append(_obs_row(user_id, obs))
        if len(rows) >= _OBS_BATCH:
            total += await _flush_obs(session, rows)
            rows = []
    return total + await _flush_obs(session, rows)


async def _flush_obs(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Insert and commit one batch of observations."""
    if not rows:
        return 0
    await session.execute(insert(ClinicalObservation), rows)
    await session.commit()
    return len(rows)


def _obs_row(user_id: str, obs: Observation) -> dict[str, Any]:
    """Build one clinical_observations insert row."""
    return {
        "id": new_uuid(),
        "user_id": user_id,
        "label": obs.label,
        "value_num": obs.value_num,
        "value_text": obs.value_text,
        "unit": obs.unit,
        "effective_at": obs.effective_at,
        "source": "apple",
        "created_at": utcnow(),
    }


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
    models = (
        HealthSample,
        Workout,
        EcgRecord,
        RouteFile,
        ClinicalObservation,
        ClinicalDocument,
    )
    for model in models:
        await session.execute(
            sql_delete(model).where(
                model.user_id == user_id, model.source == "apple"
            )
        )
    await session.commit()


async def _unlink_blobs(session: AsyncSession, user_id: str) -> None:
    """Remove ECG/route/CDA files on disk before their rows are deleted."""
    paths: list[str] = []
    for model in (EcgRecord, RouteFile, ClinicalDocument):
        rows = await session.execute(
            select(model.file_path).where(
                model.user_id == user_id, model.source == "apple"
            )
        )
        paths.extend(row[0] for row in rows)
    for path in paths:
        Path(path).unlink(missing_ok=True)
