"""Home summary tiles and the reports list."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from app.api.v1 import sync
from app.core.db import SessionFactory
from app.models.meal import Meal
from app.services import meal_ai, meal_nutrients, tally
from httpx import AsyncClient

PARIS = ZoneInfo("Europe/Paris")  # the default time zone of a user


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
    today = datetime.now(PARIS).date().isoformat()
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


async def test_home_shows_pee_and_distance_walked(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Pee and km walked are home tiles; a count prints bare ("2")."""
    for _ in range(2):
        await client.post(
            "/api/v1/sync/tally",
            json={"metric": "elimination.urination"},
            headers=auth,
        )
    item = {"metric_key": "activity.distance", "value": 6.4}
    item["date_key"] = datetime.now(UTC).date().isoformat()
    await client.post(
        "/api/v1/measurements", json={"items": [item]}, headers=auth
    )
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    by_key = {t["key"]: t for t in tiles}
    pee = by_key["elimination.urination"]
    assert (pee["value"], pee["unit"]) == (2.0, None)
    assert pee["at"]  # the time of the last pee
    walked = by_key["activity.distance"]
    assert (walked["value"], walked["unit"]) == (6.4, "km")


async def _tiles(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    tiles = (await client.get("/api/v1/summary", headers=auth)).json()
    return {t["key"]: t for t in tiles}


async def test_a_counter_shows_the_time_of_its_last_addition(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def tap_at(iso: str) -> None:
        now = datetime.fromisoformat(iso)
        monkeypatch.setattr(sync, "utcnow", lambda: now)
        monkeypatch.setattr(tally, "utcnow", lambda: now)

    tally_url = "/api/v1/sync/tally"
    # 01:30 in Paris on 25/09 is 23:30 UTC on 24/09: still that day's time
    tap_at("2026-09-24T23:30:00+00:00")
    await client.post(tally_url, json={"metric": "habit.coffee"}, headers=auth)
    coffee = (await _tiles(client, auth))["habit.coffee"]
    assert coffee["date_key"] == "2026-09-25"
    assert coffee["at"].startswith("2026-09-24T23:30")
    tap_at("2026-09-25T06:10:00+00:00")
    for key in ("habit.coffee", "water.bottles_1_5"):
        await client.post(tally_url, json={"metric": key}, headers=auth)
    tiles = await _tiles(client, auth)
    assert tiles["habit.coffee"]["value"] == 2
    assert tiles["habit.coffee"]["at"].startswith("2026-09-25T06:10")
    assert tiles["hydration.liters"]["at"].startswith("2026-09-25T06:10")
    # added afterwards for a past day: only the day is known
    past = {"metric": "habit.cigarettes", "date_key": "2026-09-20"}
    await client.post(tally_url, json=past, headers=auth)
    assert (await _tiles(client, auth))["habit.cigarettes"]["at"] is None


async def test_home_shows_the_energy_brought_by_meals(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    made = await client.post(
        "/api/v1/meals",
        data={
            "meal_type": "dinner",
            "eaten_at": "2026-09-25T05:00",
            "description": "Traitement A test",
        },
        headers=auth,
    )
    async with SessionFactory() as session:
        meal = await session.get(Meal, made.json()["id"])
        assert meal is not None
        await meal_nutrients.record(session, meal, {"energy_kcal": 363.4})
        await session.commit()
    energy = (await _tiles(client, auth))["nutrition.energy"]
    assert energy["label"] == "Énergie apportée (repas)"
    assert (energy["value"], energy["unit"]) == (363.4, "kcal")
    assert energy["date_key"] == "2026-09-25"
    at = datetime.fromisoformat(energy["at"])
    assert at == datetime(2026, 9, 25, 3, tzinfo=UTC)  # 05:00 in Paris
