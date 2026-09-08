"""Idempotent seeding: bootstrap admin + load the metric catalogue.

Run via ``python -m app.seed.seed`` (invoked by ``install.sh``). Safe to
run repeatedly: existing users/metrics are left untouched.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.metric import MetricDefinition
from app.models.user import User
from app.seed.catalog import CATALOG

_log = get_logger("seed")


async def seed() -> None:
    """Seed the admin user and metric catalogue in one transaction."""
    async with SessionFactory() as session:
        await _seed_admin(session)
        created = await _seed_catalog(session)
        await session.commit()
    _log.info("seed_complete", metrics_added=created)


def main() -> None:
    """Console entrypoint used by the installer."""
    asyncio.run(seed())


async def _seed_admin(session: AsyncSession) -> None:
    """Create the configured admin account when absent."""
    settings = get_settings()
    result = await session.execute(
        select(User).where(User.email == settings.admin_email)
    )
    if result.scalar_one_or_none() is not None:
        return
    session.add(
        User(
            email=settings.admin_email,
            display_name="Admin",
            password_hash=hash_password(settings.admin_password),
            role="admin",
            timezone=settings.default_timezone,
            unit_system=settings.default_unit_system,
        )
    )


async def _seed_catalog(session: AsyncSession) -> int:
    """Insert any catalogue metric not already present."""
    result = await session.execute(select(MetricDefinition.key))
    existing = {row[0] for row in result.all()}
    added = 0
    for entry in CATALOG:
        if entry["key"] in existing:
            continue
        session.add(MetricDefinition(**entry))
        added += 1
    return added


if __name__ == "__main__":
    main()
