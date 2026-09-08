"""Mode B capture: opens an event, records inputs, returns the form."""

from __future__ import annotations

from httpx import AsyncClient

CAPTURE = "/api/v1/capture"
MEAS = "/api/v1/measurements"


async def test_capture_opens_event_and_returns_form(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(
        CAPTURE, json={"weight": 84.0, "photo_face": True}, headers=auth
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_id"]
    assert len(data["complement"]) > 0
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    assert listed.json()[0]["value"] == 84.0


async def test_capture_prefills_recent_watch_data(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    watch = {
        "date_key": "2026-03-01",
        "samples": [{"metric_key": "sleep.spo2_min", "value": 92}],
    }
    await client.post("/api/v1/ingest/watch", json=watch, headers=auth)
    response = await client.post(CAPTURE, json={}, headers=auth)
    assert response.status_code == 201
    assert len(response.json()["prefilled"]) >= 1
