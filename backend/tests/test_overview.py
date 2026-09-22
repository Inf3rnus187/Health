"""One metric at a glance, identical on every page."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

MEAS = "/api/v1/measurements"


async def _weights(client: AsyncClient, auth: dict[str, str]) -> None:
    items = [
        {"metric_key": "body.weight", "date_key": day, "value": kg}
        for day, kg in (
            ("2026-09-01", 108.0),
            ("2026-09-10", 107.0),
            ("2026-09-20", 106.0),
        )
    ]
    resp = await client.post(MEAS, json={"items": items}, headers=auth)
    assert resp.status_code == 201


async def test_overview_numbers(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _weights(client, auth)
    resp = await client.get(
        "/api/v1/metrics/body.weight/overview", headers=auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"]["value"] == 106.0
    assert body["day"] == {"date": "2026-09-20", "value": 106.0}
    assert body["avg30"] == pytest.approx(107.0)
    assert body["avg7"] == 106.0
    assert body["days_count"] == 3
    assert body["sources"] == [{"source": "manual", "count": 3}]
    assert [p["value"] for p in body["series"]] == [108.0, 107.0, 106.0]
    assert body["day_label"] == "Moyenne du jour"


async def test_home_tile_matches_the_overview(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _weights(client, auth)
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    tile = next(t for t in tiles if t["key"] == "body.weight")
    overview = (
        await client.get("/api/v1/metrics/body.weight/overview", headers=auth)
    ).json()
    assert tile["value"] == overview["latest"]["value"]
    assert tile["avg7"] == overview["avg7"]


async def test_overview_of_an_empty_metric(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/metrics/body.waist/overview", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["latest"] is None
    assert resp.json()["series"] == []
