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
from app.models.mapping import IngestMapping
from app.models.metric import MetricDefinition
from app.models.user import User
from app.seed.catalog import CATALOG
from app.seed.mappings import DEFAULT_MAPPINGS
from app.services import canonical
from app.services.apple_health.metrics_cache import MetricCache

_log = get_logger("seed")


async def seed() -> None:
    """Seed admin, metric catalogue and default mappings."""
    async with SessionFactory() as session:
        await _seed_admin(session)
        metrics = await _seed_catalog(session)
        maps = await _seed_mappings(session)
        await session.commit()
    _log.info("seed_complete", metrics_added=metrics, mappings_added=maps)


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
        key = canonical.canonical(entry["key"])
        if key != entry["key"]:  # an alias: seed its canonical metric
            added += key not in existing
            await canonical.ensure(session, key, MetricCache())
        elif key not in existing:
            session.add(MetricDefinition(**entry))
            added += 1
    return added


async def _seed_mappings(session: AsyncSession) -> int:
    """Insert any global default ingest mapping not already present."""
    result = await session.execute(
        select(IngestMapping.source, IngestMapping.external_key).where(
            IngestMapping.user_id.is_(None)
        )
    )
    existing = {(row[0], row[1]) for row in result.all()}
    added = 0
    for source, external_key, metric_key in DEFAULT_MAPPINGS:
        if (source, external_key) in existing:
            continue
        session.add(
            IngestMapping(
                source=source,
                external_key=external_key,
                metric_key=metric_key,
            )
        )
        added += 1
    return added


if __name__ == "__main__":
    main()
