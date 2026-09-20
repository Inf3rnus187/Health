"""One-tap mobile sync: pre-filled Shortcut download + flat ingest."""

from __future__ import annotations

import plistlib

from httpx import AsyncClient

SYNC = "/api/v1/sync"
MEAS = "/api/v1/measurements"


async def _watch_token(client: AsyncClient, auth: dict[str, str]) -> str:
    """Mint an ingest:watch token and return its secret."""
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "iphone", "scopes": ["ingest:watch"]},
        headers=auth,
    )
    return str(created.json()["token"])


async def test_shortcut_download_is_valid_plist(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get(
        f"{SYNC}/shortcut", params={"base": "http://test"}, headers=auth
    )
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    workflow = plistlib.loads(response.content)
    actions = workflow["WFWorkflowActions"]
    ids = [a["WFWorkflowActionIdentifier"] for a in actions]
    assert "is.workflow.actions.downloadurl" in ids


async def test_shortcut_embeds_working_token(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """The token baked into the shortcut ingests against /sync/health."""
    response = await client.get(
        f"{SYNC}/shortcut", params={"base": "http://test"}, headers=auth
    )
    workflow = plistlib.loads(response.content)
    post = workflow["WFWorkflowActions"][2]["WFWorkflowActionParameters"]
    header = post["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"][0]
    bearer = header["WFValue"]["Value"]["string"]
    assert post["WFURL"] == "http://test/api/v1/sync/health"
    assert bearer.startswith("Bearer ")
    token = bearer.removeprefix("Bearer ")
    ingest = await client.post(
        f"{SYNC}/health",
        json={"date_key": "2026-03-01", "metrics": {"body.weight": 86.2}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ingest.json()["recorded"] == 1


async def test_sync_health_lenient_numbers(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Values like '86,2 kg' parse; garbage is reported, never fatal."""
    token = await _watch_token(client, auth)
    response = await client.post(
        f"{SYNC}/health",
        json={
            "date_key": "2026-03-02",
            "metrics": {
                "HKQuantityTypeIdentifierBodyMass": "86,2 kg",
                "HKQuantityTypeIdentifierStepCount": "8 542 pas",
                "junk.metric": "n/a",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    body = response.json()
    assert body["recorded"] == 2
    assert body["skipped"] == ["junk.metric"]
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    assert listed.json()[0]["value"] == 86.2


async def test_sync_health_requires_scope(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "ro", "scopes": ["read:all"]},
        headers=auth,
    )
    headers = {"Authorization": f"Bearer {created.json()['token']}"}
    response = await client.post(
        f"{SYNC}/health",
        json={"metrics": {"body.weight": 80}},
        headers=headers,
    )
    assert response.status_code == 403


async def test_shortcut_download_requires_user_session(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """A machine token cannot mint a shortcut (interactive users only)."""
    token = await _watch_token(client, auth)
    response = await client.get(
        f"{SYNC}/shortcut",
        params={"base": "http://test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
