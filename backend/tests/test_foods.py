"""The foods eaten often: their sheet, photos, label reading, meals."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import meal_ai
from httpx import AsyncClient
from PIL import Image

FOODS = "/api/v1/foods"
MEALS = "/api/v1/meals"
RICE = {
    "name": "Riz méditerranéen",
    "brand": "Marque test",
    "aliases": "riz sachet, riz micro-ondes",
    "package_g": 250,
    "per_100g": {
        "energy_kcal": 150,
        "protein_g": 3.5,
        "carbs_g": 30,
        "fat_g": 1.8,
        "sodium_mg": 400,
    },
}


def _jpeg(color: tuple[int, int, int] = (200, 60, 40)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(out, format="JPEG")
    return out.getvalue()


async def _rice(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    made = await client.post(FOODS, json=RICE, headers=auth)
    assert made.status_code == 201, made.text
    return dict(made.json())


async def test_a_food_sheet_with_its_photos(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    food = await _rice(client, auth)
    assert food["per_100g"]["energy_kcal"] == 150 and food["photos"] == []
    url = f"{FOODS}/{food['id']}/photos"
    shot = {"file": ("etiquette.jpg", _jpeg(), "image/jpeg")}
    added = await client.post(
        url, data={"kind": "label"}, files=shot, headers=auth
    )
    assert added.status_code == 201, added.text
    (photo,) = added.json()["photos"]
    assert photo["kind"] == "label" and "path" not in photo
    pic = await client.get(f"{url}/{photo['id']}", headers=auth)
    assert pic.headers["content-type"] == "image/jpeg"
    wrong = await client.post(
        url, data={"kind": "recu"}, files=shot, headers=auth
    )
    assert wrong.status_code == 422
    changed = await client.put(
        f"{FOODS}/{food['id']}", json={**RICE, "package_g": 125}, headers=auth
    )
    assert changed.json()["package_g"] == 125
    assert changed.json()["photos"] == added.json()["photos"]
    await client.delete(f"{url}/{photo['id']}", headers=auth)
    assert (await client.get(f"{url}/{photo['id']}", headers=auth)).is_error
    await client.delete(f"{FOODS}/{food['id']}", headers=auth)
    assert (await client.get(FOODS, headers=auth)).json() == []


async def test_impossible_label_values_are_refused(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    wrong = {**RICE, "per_100g": {"protein_g": 130}}
    res = await client.post(FOODS, json=wrong, headers=auth)
    assert res.status_code == 422


async def test_another_user_never_sees_nor_uses_my_foods(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    food = await _rice(client, auth)
    url = f"{FOODS}/{food['id']}"
    shot = {"file": ("boite.jpg", _jpeg(), "image/jpeg")}
    added = await client.post(f"{url}/photos", files=shot, headers=auth)
    photo_id = added.json()["photos"][0]["id"]
    assert (await client.get(FOODS, headers=member)).json() == []
    assert (await client.get(url, headers=member)).status_code == 404
    pic = await client.get(f"{url}/photos/{photo_id}", headers=member)
    assert pic.status_code == 404
    put = await client.put(url, json=RICE, headers=member)
    assert put.status_code == 404
    assert (await client.delete(url, headers=member)).status_code == 404
    portions = json.dumps([{"food_id": food["id"], "grams": 100}])
    meal = await client.post(
        MEALS, data={"description": "riz", "foods": portions}, headers=member
    )
    assert meal.status_code == 404
    assert (await client.get(url, headers=auth)).status_code == 200


async def test_reading_a_label_is_a_checked_proposal(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def vision(prompt: str, image: bytes, **_: Any) -> dict[str, Any]:
        assert "valeurs nutritionnelles" in prompt
        return {
            "name": "Riz méditerranéen",
            "brand": "Marque test",
            "net_g": "250 g",
            "per_100g": {
                "energy_kcal": "150",
                "protein_g": "3,5",
                "fat_g": "< 0,5",
                "sugars_g": 250,  # impossible: dropped
                "salt_g": "1",
            },
        }

    monkeypatch.setattr(ollama, "vision_json", vision)
    shot = {"file": ("etiquette.jpg", _jpeg(), "image/jpeg")}
    res = await client.post(f"{FOODS}/read-label", files=shot, headers=auth)
    assert res.status_code == 200, res.text
    read = res.json()
    assert read["package_g"] == 250
    assert read["per_100g"] == {
        "energy_kcal": 150,
        "protein_g": 3.5,
        "fat_g": 0.5,
        "sodium_mg": 400,
    }
    assert (await client.get(FOODS, headers=auth)).json() == []  # not saved


_CHICKEN = {
    "name": "Poulet",
    "grams": 100,
    "protein_g": 31,
    "carbs_g": 0,
    "fat_g": 3.6,
    "sodium_mg": 70,
}


async def test_a_meal_with_its_sachet_is_read_from_the_label(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    food = await _rice(client, auth)

    async def no_worker(*_: Any) -> bool:
        return False

    async def vision(prompt: str, image: Any, **_: Any) -> dict[str, Any]:
        assert len(image) == 3 and '"labels"' in prompt
        return {"items": [{"name": "riz", "grams": 200}], "labels": []}

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        if "Juge ce repas" in prompt:  # 2nd call: the code's exact values
            line = "Riz méditerranéen · Marque test · 250 g : 125 g"
            assert f"{line} (saisis par le patient, étiquette)" in prompt
            assert "énergie 187,5 kcal" in prompt
            return {"score": 6, "verdict": "Correct"}
        assert "Étiquettes des produits" in prompt and food["id"] in prompt
        guess = {"name": "Riz", "grams": 200, "protein_g": 5, "carbs_g": 60}
        return {"items": [{**guess, "food_id": food["id"]}, _CHICKEN]}

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "vision_json", vision)
    monkeypatch.setattr(ollama, "text_json", text)
    shots = [
        ("file", ("assiette.jpg", _jpeg(), "image/jpeg")),
        ("photos", ("sachet.jpg", _jpeg((10, 90, 200)), "image/jpeg")),
        ("photos", ("valeurs.jpg", _jpeg((240, 240, 240)), "image/jpeg")),
    ]
    portions = json.dumps([{"food_id": food["id"], "grams": 125}])
    made = await client.post(
        MEALS,
        data={"description": "riz sachet et poulet", "foods": portions},
        files=shots,
        headers=auth,
    )
    assert made.status_code == 201, made.text
    meal = made.json()
    assert len(meal["photo_ids"]) == 2 and meal["foods"][0]["grams"] == 125
    async with SessionFactory() as session:
        await meal_ai.run(session, meal["id"])
    read = (await client.get(f"{MEALS}/{meal['id']}", headers=auth)).json()
    rice, chicken = read["analysis"]["items"]
    assert (rice["source"], rice["grams"]) == ("étiquette", 125)
    assert rice["grams_from"] == "formulaire"
    assert (read["analysis"]["score"], read["analysis"]["verdict"]) == (
        6,
        "Correct",
    )
    assert rice["energy_kcal"] == pytest.approx(187.5)
    assert rice["protein_g"] == pytest.approx(4.4)
    assert rice["sodium_mg"] == 500
    assert chicken["name"] == "Poulet" and "source" not in chicken
    assert read["analysis"]["foods"] == [
        "Riz méditerranéen · Marque test · 250 g"
    ]
    extra = f"{MEALS}/{meal['id']}/photos/{meal['photo_ids'][0]}"
    assert (await client.get(extra, headers=auth)).status_code == 200
    gone = await client.delete(extra, headers=auth)
    assert len(gone.json()["photo_ids"]) == 1


async def test_a_food_named_in_a_meal_is_found_without_picking_it(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    await _rice(client, auth)

    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        assert "Riz méditerranéen" in prompt and "250" in prompt
        return {"items": [_CHICKEN]}  # the rice forgotten

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        MEALS,
        data={"description": "Poulet et Riz micro-ondes"},
        headers=auth,
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    read = await client.get(f"{MEALS}/{made.json()['id']}", headers=auth)
    names = [i["name"] for i in read.json()["analysis"]["items"]]
    assert names == ["Poulet", "Riz méditerranéen · Marque test · 250 g"]
    assert read.json()["analysis"]["items"][1]["grams"] == 250
