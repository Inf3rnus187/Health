"""A meal changed afterwards: text, time, foods, photos added or removed."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from app.services import meal_ai
from httpx import AsyncClient
from PIL import Image

MEALS = "/api/v1/meals"


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (64, 48), (20, 160, 90)).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The meals handed to the worker (none really runs)."""
    seen: list[str] = []

    async def worker(_: str, meal_id: str) -> bool:
        seen.append(meal_id)
        return True

    monkeypatch.setattr(meal_ai, "enqueue", worker)
    return seen


async def test_photos_added_and_removed_afterwards(
    client: AsyncClient, auth: dict[str, str], queued: list[str]
) -> None:
    made = await client.post(
        MEALS, data={"description": "salade"}, headers=auth
    )
    meal = made.json()
    assert not meal["has_photo"]
    url = f"{MEALS}/{meal['id']}/photos"
    shot = {"file": ("plat.jpg", _jpeg(), "image/jpeg")}
    first = await client.post(url, files=shot, headers=auth)
    assert first.json()["has_photo"] and first.json()["photo_ids"] == []
    queued.clear()
    second = await client.post(
        url, files=shot, params={"read": "false"}, headers=auth
    )
    assert len(second.json()["photo_ids"]) == 1
    assert queued == []  # read=false: no new reading yet
    gone = await client.delete(
        f"{MEALS}/{meal['id']}/photo", params={"read": "false"}, headers=auth
    )
    assert not gone.json()["has_photo"] and len(gone.json()["photo_ids"]) == 1
    pic = await client.get(f"{MEALS}/{meal['id']}/photo", headers=auth)
    assert pic.status_code == 404
    extra = second.json()["photo_ids"][0]
    await client.delete(f"{url}/{extra}", headers=auth)
    assert queued == [meal["id"]]


async def test_text_time_and_foods_changed(
    client: AsyncClient, auth: dict[str, str], queued: list[str]
) -> None:
    food = await client.post(
        "/api/v1/foods", json={"name": "Comté", "unit_g": 30}, headers=auth
    )
    made = await client.post(
        MEALS,
        data={"description": "pain", "eaten_at": "2026-09-20T12:00"},
        headers=auth,
    )
    change: dict[str, Any] = {
        "description": "pain et une tranche de comté",
        "eaten_at": "2026-09-20T19:30:00+02:00",
        "meal_type": "dinner",
        "foods": [{"food_id": food.json()["id"], "grams": None}],
    }
    res = await client.put(
        f"{MEALS}/{made.json()['id']}", json=change, headers=auth
    )
    meal = res.json()
    assert (meal["meal_type"], meal["date_key"]) == ("dinner", "2026-09-20")
    assert meal["description"] == "pain et une tranche de comté"
    assert meal["foods"] == [{"food_id": food.json()["id"], "grams": None}]
    assert queued[-1] == meal["id"]
    cleared = await client.put(
        f"{MEALS}/{meal['id']}", json={"foods": []}, headers=auth
    )
    assert cleared.json()["foods"] == []
    assert json.loads(cleared.text)["description"].startswith("pain")
