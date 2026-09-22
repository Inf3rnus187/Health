"""Home summary tiles and the reports list."""

from __future__ import annotations

from datetime import UTC, datetime

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
    # Entered later for a past day: only the day is known, no made-up time.
    assert weight["at"] is None
    today = datetime.now(UTC).date().isoformat()
    body["items"][0]["date_key"] = today
    await client.post("/api/v1/measurements", json=body, headers=auth)
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    weight = next(t for t in tiles if t["key"] == "body.weight")
    assert weight["at"]  # typed on its own day: the entry time


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


async def test_summary_prefers_latest_reading_for_instant_metric(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """An instant metric's tile shows the latest reading, not the day mean."""
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "s", "scopes": ["write:measurements"]},
        headers=auth,
    )
    token = created.json()["token"]
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "heart_rate",
                    "units": "count/min",
                    "data": [
                        {"date": "2026-05-01 08:00:00 +0000", "Avg": 60},
                        {"date": "2026-05-01 20:00:00 +0000", "Avg": 80},
                    ],
                }
            ]
        }
    }
    await client.post(f"/api/v1/sync/auto-export?token={token}", json=payload)
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    hr = next(t for t in tiles if t["key"] == "heart.rate")
    assert hr["value"] == 80
