"""Reading health data with a token needs read:all (or hub:full)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_READS = (
    "/api/v1/export",
    "/api/v1/measurements",
    "/api/v1/summary",
    "/api/v1/samples",
    "/api/v1/metrics/body.weight/overview",
    "/api/v1/measurements/series?metric_key=body.weight",
    "/api/v1/trends?metric_key=body.weight",
    "/api/v1/dashboard/body",
    "/api/v1/evolution/markers",
    "/api/v1/photos",
    "/api/v1/reports",
    "/api/v1/workouts",
    "/api/v1/clinical/observations",
)


async def _token(
    client: AsyncClient, auth: dict[str, str], scopes: list[str]
) -> dict[str, str]:
    created = await client.post(
        "/api/v1/tokens", json={"name": "t", "scopes": scopes}, headers=auth
    )
    assert created.status_code == 201, created.text
    return {"Authorization": f"Bearer {created.json()['token']}"}


@pytest.mark.parametrize(
    "scope", ["ingest:watch", "write:measurements", "ingest:photo"]
)
async def test_write_only_tokens_cannot_read_health_data(
    client: AsyncClient, auth: dict[str, str], scope: str
) -> None:
    token = await _token(client, auth, [scope])
    for path in _READS:
        res = await client.get(path, headers=token)
        assert res.status_code == 403, path
        assert res.json()["detail"] == "Missing scope: read:all"


@pytest.mark.parametrize("scope", ["read:all", "hub:full"])
async def test_read_tokens_and_sessions_can_read(
    client: AsyncClient, auth: dict[str, str], scope: str
) -> None:
    token = await _token(client, auth, [scope])
    for headers in (token, auth):
        for path in _READS:
            res = await client.get(path, headers=headers)
            assert res.status_code == 200, (path, res.text)


async def test_write_tokens_still_write(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    token = await _token(client, auth, ["write:measurements"])
    item = {"metric_key": "body.weight", "date_key": "2026-06-01", "value": 90}
    res = await client.post(
        "/api/v1/measurements", json={"items": [item]}, headers=token
    )
    assert res.status_code == 201


async def test_a_leaked_token_cannot_wipe_data(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Bulk deletions need the user (session or hub:full), not any token."""
    token = await _token(client, auth, ["write:measurements", "read:all"])
    assert (
        await client.delete("/api/v1/photos", headers=token)
    ).status_code == 403
    reset = await client.post("/api/v1/imports/reset", headers=token)
    assert reset.status_code == 403
    again = await client.post("/api/v1/evolution/reanalyze-all", headers=token)
    assert again.status_code == 403
    assert (
        await client.delete("/api/v1/photos", headers=auth)
    ).status_code == 200
