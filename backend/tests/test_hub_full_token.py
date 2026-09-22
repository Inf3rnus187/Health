"""A hub:full token (MCP server) reaches everything but account security."""

from __future__ import annotations

from httpx import AsyncClient


async def _token(
    client: AsyncClient, auth: dict[str, str], scopes: list[str]
) -> dict[str, str]:
    created = await client.post(
        "/api/v1/tokens", json={"name": "mcp", "scopes": scopes}, headers=auth
    )
    assert created.status_code == 201, created.text
    return {"Authorization": f"Bearer {created.json()['token']}"}


async def test_hub_full_token_reaches_the_record_and_data(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    mcp = await _token(client, auth, ["hub:full"])
    for path in (
        "/api/v1/medical/record",
        "/api/v1/care/overview",
        "/api/v1/medical/documents",
        "/api/v1/data/inventory",
        "/api/v1/conditions",
        "/api/v1/evolution/markers",
    ):
        assert (await client.get(path, headers=mcp)).status_code == 200, path
    added = await client.post(
        "/api/v1/conditions", json={"name": "Asthme"}, headers=mcp
    )
    assert added.status_code == 201
    item = {"metric_key": "body.weight", "date_key": "2026-06-01", "value": 90}
    wrote = await client.post(
        "/api/v1/measurements", json={"items": [item]}, headers=mcp
    )
    assert wrote.status_code == 201


async def test_hub_full_token_cannot_manage_account_security(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    mcp = await _token(client, auth, ["hub:full"])
    minted = await client.post(
        "/api/v1/tokens",
        json={"name": "x", "scopes": ["read:all"]},
        headers=mcp,
    )
    assert minted.status_code == 403
    assert (await client.get("/api/v1/tokens", headers=mcp)).status_code == 403
    assert (await client.delete("/api/v1/me", headers=mcp)).status_code == 403
    setup = await client.post("/api/v1/auth/mfa/setup", headers=mcp)
    assert setup.status_code == 403
    shortcut = await client.get("/api/v1/sync/shortcut", headers=mcp)
    assert shortcut.status_code == 403


async def test_other_tokens_stay_out_of_the_record(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    ingest = await _token(client, auth, ["write:measurements"])
    record = await client.get("/api/v1/medical/record", headers=ingest)
    assert record.status_code == 403
