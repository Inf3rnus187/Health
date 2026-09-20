"""Calendar-bucketed trend endpoint."""

from __future__ import annotations

from httpx import AsyncClient

MEAS = "/api/v1/measurements"
TRENDS = "/api/v1/trends"


async def _record(
    client: AsyncClient, auth: dict[str, str], key: str, value: float, day: str
) -> None:
    body = {"items": [{"metric_key": key, "date_key": day, "value": value}]}
    response = await client.post(MEAS, json=body, headers=auth)
    assert response.status_code == 201


async def test_weekly_average(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _record(client, auth, "body.weight", 80.0, "2026-01-05")
    await _record(client, auth, "body.weight", 81.0, "2026-01-06")
    await _record(client, auth, "body.weight", 79.0, "2026-01-12")
    trend = await client.get(
        TRENDS,
        params={"metric_key": "body.weight", "bucket": "week"},
        headers=auth,
    )
    points = trend.json()["points"]
    assert points == [
        {"date_key": "2026-01-05", "value": 80.5},
        {"date_key": "2026-01-12", "value": 79.0},
    ]


async def test_monthly_sum(client: AsyncClient, auth: dict[str, str]) -> None:
    await _record(client, auth, "stairs.floors", 10, "2026-01-05")
    await _record(client, auth, "stairs.floors", 5, "2026-01-20")
    trend = await client.get(
        TRENDS,
        params={"metric_key": "stairs.floors", "bucket": "month"},
        headers=auth,
    )
    points = trend.json()["points"]
    assert points == [{"date_key": "2026-01-01", "value": 15.0}]


async def test_invalid_bucket_rejected(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get(
        TRENDS,
        params={"metric_key": "body.weight", "bucket": "decade"},
        headers=auth,
    )
    assert response.status_code == 422
