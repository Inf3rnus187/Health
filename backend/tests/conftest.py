"""Shared fixtures: env, isolated SQLite DB, seeded data, HTTP client."""

from __future__ import annotations

import os
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789-abcdef!!")
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./.pytest_phoenix.db"
)
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass123")
os.environ.setdefault("MEDIA_DIR", "./.pytest_media")
os.environ.setdefault("EXPORTS_DIR", "./.pytest_exports")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.seed.seed import seed  # noqa: E402
from app.workers import queue  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture(autouse=True)
def _no_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """No Redis in tests: fail a queueing at once (arq retries ~5 s)."""

    async def unreachable(*_: object, **__: object) -> None:
        raise ConnectionError("no Redis in tests")

    monkeypatch.setattr(queue, "create_pool", unreachable)


async def _fresh_schema() -> None:
    """Rebuild the schema and seed it (admin, catalogue, mappings)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed()


def _sqlite_file() -> Path | None:
    """The test database file, or None when it is not SQLite."""
    name = engine.url.database
    if engine.url.get_backend_name() != "sqlite" or not name:
        return None
    return Path(name)


#: Set once the seeded template of this run exists.
_TEMPLATE_READY: list[Path] = []


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db() -> AsyncGenerator[None, None]:
    """A freshly seeded database for each test.

    Seeding takes ~0.35 s; it runs once per session and each test gets a
    copy of that seeded file (SQLite), so 200 tests do not seed 200 times.
    """
    path = _sqlite_file()
    if path is None:
        await _fresh_schema()
    elif not _TEMPLATE_READY:
        await _fresh_schema()
        await engine.dispose()
        template = path.with_name(path.name + ".seeded")
        shutil.copyfile(path, template)
        _TEMPLATE_READY.append(template)
    else:
        await engine.dispose()
        shutil.copyfile(_TEMPLATE_READY[0], path)
    yield
    await engine.dispose()


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


@pytest_asyncio.fixture
async def member(client: AsyncClient) -> dict[str, str]:
    """An Authorization header for a second, ordinary user (role user)."""
    from app.core.db import SessionFactory
    from app.core.security import hash_password
    from app.models.user import User

    async with SessionFactory() as session:
        session.add(
            User(
                email="membre@example.com",
                display_name="Membre",
                password_hash=hash_password("motdepasse-membre-123"),
                role="user",
            )
        )
        await session.commit()
    creds = {"email": "membre@example.com", "password": "motdepasse-membre-123"}
    login = await client.post("/api/v1/auth/login", json=creds)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}
