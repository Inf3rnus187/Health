"""Scoped API tokens: creation, scope enforcement and revocation."""

from __future__ import annotations

from httpx import AsyncClient

TOKENS = "/api/v1/tokens"
MEAS = "/api/v1/measurements"


async def _make_token(
    client: AsyncClient, auth: dict[str, str], scopes: list[str]
) -> str:
    response = await client.post(
        TOKENS, json={"name": "script", "scopes": scopes}, headers=auth
    )
    assert response.status_code == 201
    return response.json()["token"]


async def test_token_can_write_with_scope(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    secret = await _make_token(client, auth, ["write:measurements"])
    headers = {"Authorization": f"Bearer {secret}"}
    body = {
        "items": [
            {
                "metric_key": "body.weight",
                "date_key": "2026-02-01",
                "value": 84.0,
            }
        ]
    }
    response = await client.post(MEAS, json=body, headers=headers)
    assert response.status_code == 201


async def test_token_without_scope_is_forbidden(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    secret = await _make_token(client, auth, ["read:all"])
    headers = {"Authorization": f"Bearer {secret}"}
    body = {
        "items": [
            {
                "metric_key": "body.weight",
                "date_key": "2026-02-01",
                "value": 84.0,
            }
        ]
    }
    response = await client.post(MEAS, json=body, headers=headers)
    assert response.status_code == 403


async def test_token_cannot_manage_tokens(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    secret = await _make_token(client, auth, ["read:all"])
    headers = {"Authorization": f"Bearer {secret}"}
    response = await client.get(TOKENS, headers=headers)
    assert response.status_code == 403


async def test_revoked_token_is_rejected(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        TOKENS,
        json={"name": "temp", "scopes": ["read:all"]},
        headers=auth,
    )
    token_id = created.json()["id"]
    secret = created.json()["token"]
    await client.delete(f"{TOKENS}/{token_id}", headers=auth)
    headers = {"Authorization": f"Bearer {secret}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


async def test_unknown_scope_rejected(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(
        TOKENS,
        json={"name": "bad", "scopes": ["do:everything"]},
        headers=auth,
    )
    assert response.status_code == 422
