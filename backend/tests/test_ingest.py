"""Ingestion: Watch/CPAP samples, HealthKit mapping, scopes."""

from __future__ import annotations

from httpx import AsyncClient

INGEST = "/api/v1/ingest"
MEAS = "/api/v1/measurements"


async def test_watch_ingest_direct_metric_key(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "date_key": "2026-03-01",
        "samples": [{"metric_key": "sleep.spo2_min", "value": 91}],
    }
    response = await client.post(f"{INGEST}/watch", json=body, headers=auth)
    assert response.status_code == 200
    assert response.json()["recorded"] == 1


async def test_watch_ingest_via_healthkit_mapping(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "date_key": "2026-03-01",
        "samples": [
            {
                "healthkit_type": "HKQuantityTypeIdentifierBodyMass",
                "value": 85.2,
            }
        ],
    }
    response = await client.post(f"{INGEST}/watch", json=body, headers=auth)
    assert response.json()["recorded"] == 1
    listed = await client.get(
        MEAS, params={"metric_key": "body.weight"}, headers=auth
    )
    assert listed.json()[0]["value"] == 85.2


async def test_unknown_healthkit_type_is_skipped(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "date_key": "2026-03-01",
        "samples": [{"healthkit_type": "HKUnknownThing", "value": 1}],
    }
    response = await client.post(f"{INGEST}/watch", json=body, headers=auth)
    assert response.json()["recorded"] == 0
    assert "HKUnknownThing" in response.json()["skipped"]


async def test_ppc_ingest(client: AsyncClient, auth: dict[str, str]) -> None:
    body = {
        "date_key": "2026-03-01",
        "samples": [
            {"metric_key": "ppc.ahi", "value": 3.2},
            {"healthkit_type": "UsageHours", "value": 6.5},
        ],
    }
    response = await client.post(f"{INGEST}/ppc", json=body, headers=auth)
    assert response.json()["recorded"] == 2


async def test_ingest_scope_enforced(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "ro", "scopes": ["read:all"]},
        headers=auth,
    )
    headers = {"Authorization": f"Bearer {created.json()['token']}"}
    body = {
        "date_key": "2026-03-01",
        "samples": [{"metric_key": "sleep.spo2_min", "value": 90}],
    }
    response = await client.post(f"{INGEST}/watch", json=body, headers=headers)
    assert response.status_code == 403


async def test_mapping_create_then_resolves(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        f"{INGEST}/mappings",
        json={
            "source": "watch",
            "external_key": "HKCustomX",
            "metric_key": "body.weight",
        },
        headers=auth,
    )
    assert created.status_code == 201
    body = {
        "date_key": "2026-03-02",
        "samples": [{"healthkit_type": "HKCustomX", "value": 80}],
    }
    response = await client.post(f"{INGEST}/watch", json=body, headers=auth)
    assert response.json()["recorded"] == 1
