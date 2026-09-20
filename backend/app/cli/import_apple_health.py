r"""Import an Apple Health export from the command line (power users).

The web UI (Réglages → Importer) is the normal path; this CLI runs the
exact same pipeline for very large files, against a ``.zip`` or a bare
``export.xml`` mounted into the container::

    docker compose exec api \
        python -m app.cli.import_apple_health /import/export.zip
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models.health_raw import ImportJob
from app.models.user import User
from app.services import imports


def main() -> None:
    """Parse arguments and run the import job inline."""
    args = _parse_args()
    job = asyncio.run(_run(args.path, args.email))
    print(
        f"status={job.status} samples={job.samples} "
        f"workouts={job.workouts} ecg={job.ecg} routes={job.routes}"
    )
    if job.error:
        print(f"error: {job.error}")


def _parse_args() -> argparse.Namespace:
    """Build and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import an Apple Health export (.zip or export.xml)"
    )
    parser.add_argument("path", help="Path to export.zip or export.xml")
    parser.add_argument(
        "--email", default=None, help="Target user (defaults to admin)"
    )
    return parser.parse_args()


async def _run(path: str, email: str | None) -> ImportJob:
    """Create and run one import job, returning its final state."""
    async with SessionFactory() as session:
        user = await _find_user(session, email)
        job = await imports.create_job(session, user.id, Path(path).name, path)
        await imports.run_job(session, job.id)
        return await imports.get_job(session, user.id, job.id)


async def _find_user(session: AsyncSession, email: str | None) -> User:
    """Return the target user or abort with a clear message."""
    target = email or get_settings().admin_email
    result = await session.execute(select(User).where(User.email == target))
    user = result.scalar_one_or_none()
    if user is None:
        raise SystemExit(f"No user found with email {target}")
    return user


if __name__ == "__main__":
    main()
