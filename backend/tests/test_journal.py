"""Journal: pee log and meals (photo, AI reading, checked nutrients)."""

from __future__ import annotations

import io
from typing import Any

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import meal_ai, meal_nutrition
from httpx import AsyncClient
from PIL import Image

PEE = "/api/v1/journal/urination"
MEALS = "/api/v1/meals"


async def _overview(client: AsyncClient, auth: dict[str, str], key: str) -> Any:
    res = await client.get(f"/api/v1/metrics/{key}/overview", headers=auth)
    return res.json()


async def test_pee_log_counts_per_day_and_undoes(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    first = await client.post(
        PEE, json={"at": "2026-09-20T07:10:00+02:00"}, headers=auth
    )
    assert first.status_code == 201
    second = await client.post(
        PEE, json={"at": "2026-09-20T23:40:00+02:00"}, headers=auth
    )
    assert second.json()["count"] == 2
    day = await client.get(PEE, params={"day": "2026-09-20"}, headers=auth)
    assert day.json()["count"] == 2
    view = await _overview(client, auth, "elimination.urination")
    assert view["day"] == {"date": "2026-09-20", "value": 2.0}
    for entry in (first.json(), second.json()):
        await client.delete(f"{PEE}/{entry['id']}", headers=auth)
    view = await _overview(client, auth, "elimination.urination")
    assert view["latest"] is None  # no stale total left behind


async def test_a_shortcut_token_can_tap_but_not_read(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "pipi", "scopes": ["write:measurements"]},
        headers=auth,
    )
    token = made.json()["token"]
    tap = await client.post(f"{PEE}?token={token}")
    assert tap.status_code == 201 and tap.json()["count"] == 1
    read = await client.get(PEE, headers={"Authorization": f"Bearer {token}"})
    assert read.status_code == 403


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 60, 40)).save(out, format="JPEG")
    return out.getvalue()


_ANSWER = {
    "items": [
        {
            "name": "Tomates",
            "grams": 240,
            "protein_g": 2.1,
            "carbs_g": 7.0,
            "sugars_g": 6.2,
            "fat_g": 0.5,
            "sat_fat_g": 0.1,
            "fiber_g": 2.9,
            "sodium_mg": 12,
        },
        {
            "name": "Blanc de poulet",
            "grams": 150,
            "protein_g": 46.5,
            "carbs_g": 0,
            "sugars_g": 0,
            "fat_g": 5.4,
            "sat_fat_g": 1.5,
            "fiber_g": 0,
            "sodium_mg": 110,
        },
        {
            "name": "Comté",
            "grams": 30,
            "protein_g": 8.1,
            "carbs_g": 0,
            "sugars_g": 0,
            "fat_g": 60,
            "sat_fat_g": 6,
            "fiber_g": 0,
            "sodium_mg": 190,
        },
    ],
    "score": 14,
    "verdict": "Repas équilibré, riche en protéines, sans graisse ajoutée.",
    "positives": ["Protéines maigres", "Légumes"],
    "watch": ["Pommes de terre : féculent"],
}


async def test_meal_is_read_checked_and_feeds_nutrition(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    async def vision(prompt: str, image: bytes, **_: Any) -> dict[str, Any]:
        assert image[:2] == b"\xff\xd8" and "comté" in prompt
        return {"items": [{"name": "salade tomate concombre", "grams": 300}]}

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        assert "salade tomate concombre" in prompt and "Asthme" in prompt
        return _ANSWER

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "vision_json", vision)
    monkeypatch.setattr(ollama, "text_json", text)
    await client.post(
        "/api/v1/conditions", json={"name": "Asthme"}, headers=auth
    )
    made = await client.post(
        MEALS,
        data={
            "meal_type": "lunch",
            "eaten_at": "2026-09-21T12:30",
            "description": "2 tomates, 1/2 concombre, comté, poulet, nature",
        },
        files={"file": ("repas.jpg", _jpeg(), "image/jpeg")},
        headers=auth,
    )
    assert made.status_code == 201, made.text
    meal = made.json()
    assert meal["has_photo"] and meal["date_key"] == "2026-09-21"
    async with SessionFactory() as session:
        await meal_ai.run(session, meal["id"])
    read = (await client.get(f"{MEALS}/{meal['id']}", headers=auth)).json()
    analysis = read["analysis"]
    assert read["analysis_status"] == "done"
    assert [i["name"] for i in analysis["items"]] == [
        "Tomates",
        "Blanc de poulet",
    ]
    assert analysis["rejected"][0]["name"] == "Comté"  # 60 g fat in 30 g
    assert analysis["score"] == 10  # clamped
    energy = analysis["totals"]["energy_kcal"]
    assert energy == pytest.approx(
        4 * (48.6 + 7.0) + 9 * 5.9 + 2 * 2.9, abs=0.2
    )
    view = await _overview(client, auth, "nutrition.energy")
    assert view["day"]["date"] == "2026-09-21"
    assert view["day"]["value"] == pytest.approx(energy, abs=0.1)
    pic = await client.get(f"{MEALS}/{meal['id']}/photo", headers=auth)
    assert pic.headers["content-type"] == "image/jpeg"
    await client.delete(f"{MEALS}/{meal['id']}", headers=auth)
    view = await _overview(client, auth, "nutrition.energy")
    assert view["latest"] is None  # nutrients left with the meal


async def test_a_meal_needs_a_description_or_a_photo(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    res = await client.post(MEALS, data={"meal_type": "dinner"}, headers=auth)
    assert res.status_code == 422


def test_impossible_foods_are_rejected_with_a_reason() -> None:
    kept, rejected = meal_nutrition.check(
        [
            {
                "name": "riz",
                "grams": 150,
                "carbs_g": 42,
                "protein_g": 4,
                "fat_g": 0.4,
                "fiber_g": 0.6,
                "sugars_g": 0.1,
            },
            {"name": "gâteau", "grams": 100, "carbs_g": 50, "sugars_g": 70},
            {"name": "soupe", "grams": 0},
            {"grams": 50},
        ]
    )
    assert [k["name"] for k in kept] == ["riz"]
    assert kept[0]["energy_kcal"] == pytest.approx(4 * 46 + 9 * 0.4 + 1.2)
    assert [r["reason"] for r in rejected] == [
        "sucres > glucides ou saturés > lipides",
        "quantité impossible (0 g)",
        "aliment sans nom",
    ]


async def test_a_pee_is_counted_like_a_bottle(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Same path as every one-tap count: /sync/tally, key ``metric``."""
    tally = "/api/v1/sync/tally"
    body = {"metric": "elimination.urination"}
    one = await client.post(tally, json=body, headers=auth)
    assert (one.json()["previous"], one.json()["total"]) == (0.0, 1.0)
    two = await client.post(tally, json={**body, "amount": 2}, headers=auth)
    assert two.json()["total"] == 3.0
    back = await client.post(tally, json={**body, "amount": -1}, headers=auth)
    assert back.json()["total"] == 2.0
    day = await client.get(PEE, headers=auth)
    assert day.json()["count"] == 2  # each pee kept with its time
    past = await client.post(
        tally, json={**body, "date_key": "2020-01-01"}, headers=auth
    )
    assert past.status_code == 422
    below = await client.post(tally, json={**body, "amount": -3}, headers=auth)
    assert below.status_code == 422


async def test_meal_type_defaults_to_the_hour(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    kinds = []
    for at in ("2026-09-21T07:45", "2026-09-21T12:30", "2026-09-21T20:30"):
        made = await client.post(
            MEALS, data={"description": "soupe", "eaten_at": at}, headers=auth
        )
        kinds.append(made.json()["meal_type"])
    assert kinds == ["breakfast", "lunch", "dinner"]


async def test_a_meal_shortcut_like_the_iphone_sends_it(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token in the URL, yesterday's time day first, empty optional fields."""

    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "repas", "scopes": ["write:measurements"]},
        headers=auth,
    )
    url = f"{MEALS}?token={made.json()['token']}"
    bare = await client.post(
        url,
        data={"description": "pâtes", "eaten_at": "23/09/2026 20:30",
              "file": "", "meal_type": ""},
    )  # fmt: skip
    assert bare.status_code == 201, bare.text
    meal = bare.json()
    assert (meal["date_key"], meal["meal_type"]) == ("2026-09-23", "dinner")
    assert not meal["has_photo"] and meal["price"] is None
    shot = await client.post(
        url,
        data={"description": "salade", "eaten_at": "2026-09-23T12:15:00+02:00",
              "price": "12,50"},  # a health meal: no price, not a proof
        files={"file": ("IMG_0001.JPG", _jpeg(), "application/octet-stream")},
    )  # fmt: skip
    assert shot.status_code == 201, shot.text
    assert shot.json()["has_photo"] and shot.json()["price"] is None
    proofs = (await client.get("/api/v1/evidence", headers=auth)).json()
    assert proofs == []
    assert shot.json()["meal_type"] == "lunch"
    wrong = await client.post(url, data={"eaten_at": "hier"})
    assert wrong.status_code == 422
