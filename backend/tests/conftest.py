"""Shared fixtures: env, isolated SQLite DB, seeded data, HTTP client."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789-abcdef!!")
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./.pytest_phoenix.db"
)
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass123")
os.environ.setdefault("MEDIA_DIR", "./.pytest_media")
os.environ.setdefault("EXPORTS_DIR", "./.pytest_exports")

import pytest_asyncio  # noqa: E402
from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed.seed import seed  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db() -> AsyncGenerator[None, None]:
    """Reset the schema and seed data around each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Yield an HTTP client bound to the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> dict[str, str]:
    """Return an Authorization header for the seeded admin user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
