"""Async database engine, session factory and request dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()
#: PostgreSQL: a bounded pool per process (SQLite, in tests: its own).
_POOLED = not _settings.database_url.startswith("sqlite")

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.debug,
    pool_pre_ping=True,
    future=True,
    # Up to 10 connections per process: API_WORKERS processes, plus the
    # worker's, stay under PostgreSQL's 100 (see API_WORKERS).
    **({"pool_size": 5, "max_overflow": 5} if _POOLED else {}),
)

SessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped session, closed on teardown."""
    async with SessionFactory() as session:
        yield session
