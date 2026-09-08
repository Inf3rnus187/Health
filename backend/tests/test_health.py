"""Health probe and unauthenticated access."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 401
