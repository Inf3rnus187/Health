"""Per-domain dashboard series."""

from __future__ import annotations

from httpx import AsyncClient

MEAS = "/api/v1/measurements"


async def test_domain_dashboard_returns_series(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for day, value in (("2026-05-01", 90.0), ("2026-05-02", 88.0)):
        body = {
            "items": [
                {"metric_key": "body.weight", "date_key": day, "value": value}
            ]
        }
        await client.post(MEAS, json=body, headers=auth)
    response = await client.get("/api/v1/dashboard/body", headers=auth)
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "body"
    weight = next(s for s in data["series"] if s["metric_key"] == "body.weight")
    assert weight["points"][-1]["value"] == 89.0


async def test_empty_domain_has_empty_points(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get("/api/v1/dashboard/walk", headers=auth)
    assert response.status_code == 200
    for entry in response.json()["series"]:
        assert entry["points"] == []
