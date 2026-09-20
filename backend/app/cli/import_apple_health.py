r"""Import an Apple Health ``export.xml`` from the command line.

Run inside the API container against a mounted export, for example::

    docker compose exec api \\
        python -m app.cli.import_apple_health /import/export.xml

Use ``--email`` to target a user other than the configured admin.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.logging import get_logger
from app.models.user import User
from app.services.apple_health.importer import ImportSummary, run_import

_log = get_logger("apple_import")


def main() -> None:
    """Parse arguments and run the import."""
    args = _parse_args()
    summary = asyncio.run(_run(args.path, args.email))
    print(
        f"Imported {summary.rows} daily values; "
        f"{summary.metrics_added} new metrics created."
    )


def _parse_args() -> argparse.Namespace:
    """Build and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import an Apple Health export.xml"
    )
    parser.add_argument("path", help="Path to the export.xml file")
    parser.add_argument(
        "--email", default=None, help="Target user (defaults to admin)"
    )
    return parser.parse_args()


async def _run(path: str, email: str | None) -> ImportSummary:
    """Resolve the user and import the export in one session."""
    async with SessionFactory() as session:
        user = await _find_user(session, email)
        summary = await run_import(session, user.id, path)
    _log.info(
        "apple_import_done",
        rows=summary.rows,
        metrics_added=summary.metrics_added,
    )
    return summary


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
