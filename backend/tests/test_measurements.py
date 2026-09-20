"""Measurements: idempotent batch, validation, series and events."""

from __future__ import annotations

from httpx import AsyncClient

MEAS = "/api/v1/measurements"


async def _record(
    client: AsyncClient,
    auth: dict[str, str],
    key: str,
    value: object,
    day: str,
) -> None:
    body = {"items": [{"metric_key": key, "date_key": day, "value": value}]}
    response = await client.post(MEAS, json=body, headers=auth)
    assert response.status_code == 201


async def test_record_is_idempotent(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _record(client, auth, "body.weight", 88.0, "2026-01-01")
    await _record(client, auth, "body.weight", 87.5, "2026-01-01")
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["value"] == 87.5


async def test_bounds_rejected(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {
                "metric_key": "sleep.spo2_min",
                "date_key": "2026-01-02",
                "value": 150,
            }
        ]
    }
    response = await client.post(MEAS, json=body, headers=auth)
    assert response.status_code == 422


async def test_derived_metric_is_read_only(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {
                "metric_key": "hydration.liters",
                "date_key": "2026-01-02",
                "value": 3.0,
            }
        ]
    }
    response = await client.post(MEAS, json=body, headers=auth)
    assert response.status_code == 422


async def test_rolling_series(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for day, value in (("2026-01-01", 90.0), ("2026-01-02", 80.0)):
        await _record(client, auth, "body.weight", value, day)
    response = await client.get(
        f"{MEAS}/series",
        params={"metric_key": "body.weight", "agg": "avg", "window": 7},
        headers=auth,
    )
    assert response.status_code == 200
    points = response.json()["points"]
    assert points[-1]["value"] == 85.0


async def test_delete_one_measurement(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {"metric_key": "body.weight", "date_key": "2026-08-01", "value": 90}
        ]
    }
    created = await client.post(MEAS, json=body, headers=auth)
    row_id = created.json()[0]["id"]
    deleted = await client.delete(f"{MEAS}/{row_id}", headers=auth)
    assert deleted.status_code == 200
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    assert listed.json() == []


async def test_delete_many_measurements(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {
                "metric_key": "body.weight",
                "date_key": "2026-08-01",
                "value": 90,
            },
            {
                "metric_key": "body.weight",
                "date_key": "2026-08-02",
                "value": 89,
            },
        ]
    }
    created = await client.post(MEAS, json=body, headers=auth)
    ids = [row["id"] for row in created.json()]
    result = await client.post(
        f"{MEAS}/delete", json={"ids": ids}, headers=auth
    )
    assert result.status_code == 200
    assert result.json()["deleted"] == 2
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    assert listed.json() == []


async def test_event_scoped_measurements(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    event = await client.post(
        "/api/v1/events",
        json={"type": "workout_block", "meta": {"block": "bike"}},
        headers=auth,
    )
    event_id = event.json()["id"]
    body = {
        "items": [
            {
                "metric_key": "workout.duration",
                "date_key": "2026-01-03",
                "value": 20,
            }
        ]
    }
    attached = await client.post(
        f"/api/v1/events/{event_id}/measurements",
        json=body,
        headers=auth,
    )
    assert attached.status_code == 201
    listed = await client.get(MEAS, params={"event_id": event_id}, headers=auth)
    assert len(listed.json()) == 1
