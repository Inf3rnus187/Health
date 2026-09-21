"""Home summary tiles and the reports list."""

from __future__ import annotations

from httpx import AsyncClient


async def test_summary_returns_latest(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {
                "metric_key": "body.weight",
                "date_key": "2026-01-10",
                "value": 80.0,
            }
        ]
    }
    await client.post("/api/v1/measurements", json=body, headers=auth)
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    weight = next(t for t in tiles if t["key"] == "body.weight")
    assert weight["value"] == 80.0
    assert weight["date_key"] == "2026-01-10"
    assert weight["at"]  # last-reading time (falls back to recorded_at)


async def test_summary_shows_habit_and_water_tiles(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {
        "items": [
            {
                "metric_key": "habit.cigarettes",
                "date_key": "2026-01-10",
                "value": 3,
            },
            {
                "metric_key": "water.bottles_1_5",
                "date_key": "2026-01-10",
                "value": 2,
            },
        ]
    }
    await client.post("/api/v1/measurements", json=body, headers=auth)
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    cigs = next(t for t in tiles if t["key"] == "habit.cigarettes")
    assert cigs["value"] == 3
    water = next(t for t in tiles if t["key"] == "hydration.liters")
    assert water["value"] == 3.0  # 2 bottles * 1.5 L
    assert water["unit"] == "L"


async def test_reports_list(client: AsyncClient, auth: dict[str, str]) -> None:
    created = await client.post(
        "/api/v1/reports", json={"type": "json"}, headers=auth
    )
    assert created.status_code == 202
    listed = (await client.get("/api/v1/reports", headers=auth)).json()
    assert any(r["id"] == created.json()["id"] for r in listed)
