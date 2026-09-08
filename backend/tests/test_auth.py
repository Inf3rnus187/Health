"""Authentication: login, profile, refresh rotation and logout."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

LOGIN = "/api/v1/auth/login"


async def _login(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    return response.json()


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    body = await _login(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_rejects_bad_password(client: AsyncClient) -> None:
    response = await client.post(
        LOGIN, json={"email": ADMIN_EMAIL, "password": "wrong"}
    )
    assert response.status_code == 401


async def test_me_returns_current_user(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get("/api/v1/auth/me", headers=auth)
    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL
    assert response.json()["role"] == "admin"


async def test_refresh_rotates_and_revokes_old(
    client: AsyncClient,
) -> None:
    first = await _login(client)
    rotated = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert rotated.status_code == 200
    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reuse.status_code == 401


async def test_logout_revokes_session(client: AsyncClient) -> None:
    body = await _login(client)
    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": body["refresh_token"]},
    )
    after = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert after.status_code == 401
