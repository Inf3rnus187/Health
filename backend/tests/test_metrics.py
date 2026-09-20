"""Dynamic metric registry: catalogue, creation and updates."""

from __future__ import annotations

from httpx import AsyncClient

METRICS = "/api/v1/metrics"


async def test_catalogue_is_seeded(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get(METRICS, headers=auth)
    assert response.status_code == 200
    keys = {m["key"] for m in response.json()}
    assert "body.weight" in keys
    assert "hydration.liters" in keys


async def test_catalog_alias_matches_metrics(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    metrics = await client.get(METRICS, headers=auth)
    catalog = await client.get("/api/v1/catalog", headers=auth)
    assert catalog.status_code == 200
    assert len(catalog.json()) == len(metrics.json())


async def test_create_metric_at_runtime(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    payload = {
        "key": "custom.mood",
        "label": "Humeur test",
        "domain": "custom",
        "data_type": "score",
        "min_value": 0,
        "max_value": 10,
    }
    created = await client.post(METRICS, json=payload, headers=auth)
    assert created.status_code == 201
    fetched = await client.get(f"{METRICS}/custom.mood", headers=auth)
    assert fetched.status_code == 200
    assert fetched.json()["label"] == "Humeur test"


async def test_duplicate_metric_conflicts(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    payload = {
        "key": "body.weight",
        "label": "dup",
        "domain": "body",
        "data_type": "float",
    }
    response = await client.post(METRICS, json=payload, headers=auth)
    assert response.status_code == 409


async def test_filter_by_domain(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get(METRICS, params={"domain": "ppc"}, headers=auth)
    assert response.status_code == 200
    domains = {m["domain"] for m in response.json()}
    assert domains == {"ppc"}


async def test_update_metric(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.patch(
        f"{METRICS}/body.weight",
        json={"label": "Poids (test)"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Poids (test)"
