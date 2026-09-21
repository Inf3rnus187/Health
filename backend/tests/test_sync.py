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


async def _write_token(client: AsyncClient, auth: dict[str, str]) -> str:
    """Mint a write:measurements token and return its secret."""
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "iphone-tally", "scopes": ["write:measurements"]},
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


async def test_tally_accumulates_with_query_token(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Each tap adds to the day's total; the token rides in the URL."""
    token = await _write_token(client, auth)
    url = f"{SYNC}/tally?token={token}"
    first = await client.post(url, json={"metric": "habit.cigarettes"})
    assert first.status_code == 200
    assert first.json()["total"] == 1.0
    second = await client.post(url, json={"metric": "habit.cigarettes"})
    assert second.json()["total"] == 2.0


async def test_tally_half_mug_coffee(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """A half mug (0.5) then a full one sums to 1.5 on an int metric."""
    token = await _write_token(client, auth)
    url = f"{SYNC}/tally?token={token}"
    await client.post(url, json={"metric": "habit.coffee", "amount": 0.5})
    full = await client.post(url, json={"metric": "habit.coffee", "amount": 1})
    assert full.json()["total"] == 1.5


async def test_tally_water_bottle_default_amount(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Omitting the amount adds one 1.5 L bottle."""
    token = await _write_token(client, auth)
    result = await client.post(
        f"{SYNC}/tally",
        json={"metric": "water.bottles_1_5"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert result.json()["total"] == 1.0


async def test_auto_export_json_body(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Health Auto Export JSON (no file) maps names and records points."""
    token = await _write_token(client, auth)
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "units": "count",
                    "data": [
                        {"date": "2026-02-01 00:00:00 +0000", "qty": 8432}
                    ],
                },
                {
                    "name": "heart_rate",
                    "units": "count/min",
                    "data": [{"date": "2026-02-01 12:00:00 +0000", "Avg": 72}],
                },
            ]
        }
    }
    res = await client.post(f"{SYNC}/auto-export?token={token}", json=payload)
    assert res.status_code == 200
    assert res.json()["recorded"] == 2
    steps = await client.get(
        MEAS, params={"metric_key": "activity.steps"}, headers=auth
    )
    row = steps.json()[0]
    assert row["value_num"] == 8432
    assert row["date_key"] == "2026-02-01"


async def test_auto_export_dedups_intraday_points(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Many points on one day collapse to one row (last wins), tz-aware."""
    token = await _write_token(client, auth)
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "units": "count",
                    "data": [
                        {"date": "2026-03-01 08:00:00 +0200", "qty": 100},
                        {"date": "2026-03-01 20:00:00 +0200", "qty": 9000},
                    ],
                }
            ]
        }
    }
    res = await client.post(f"{SYNC}/auto-export?token={token}", json=payload)
    assert res.status_code == 200
    assert res.json()["recorded"] == 1
    steps = await client.get(
        MEAS, params={"metric_key": "activity.steps"}, headers=auth
    )
    rows = steps.json()
    assert len(rows) == 1
    assert rows[0]["value_num"] == 9000
    assert rows[0]["date_key"] == "2026-03-01"


def test_auto_export_timestamps_are_tz_aware() -> None:
    from app.services.auto_export import _ts

    offset = _ts("2026-03-01 08:00:00 +0200")
    assert offset is not None and offset.tzinfo is not None
    naive = _ts("2026-03-01")
    assert naive is not None and naive.tzinfo is not None
