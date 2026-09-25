"""Open Food Facts: every detail of the page is kept, and trusted."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.core import ollama
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.services import food_off, meal_ai
from httpx import AsyncClient

CODE = "2001234567893"
PRODUCT = {
    "product_name_fr": "Aubergines cuisinées à la provençale",
    "brands": "Marque test",
    "product_quantity": 185,
    "nutriments": {
        "energy-kcal_100g": 83, "energy_100g": 344, "fat_100g": 5.2,
        "saturated-fat_100g": 0.6, "carbohydrates_100g": 6.7,
        "sugars_100g": 5.6, "fiber_100g": 2.2, "proteins_100g": 1.2,
        "salt_100g": 0.76, "sodium_100g": 0.304,
        "fruits-vegetables-legumes-estimate-from-ingredients_100g": 96.05,
        "fruits-vegetables-nuts_100g": 80.7,  # older field: not the page's
        "potassium_100g": 0.21, "vitamin-c_100g": 0.004,
    },
    "ingredients_text_fr": "Aubergines 60 %, tomates, oignons, huile de "
    "tournesol, _céleri_, sel, acidifiant : acide citrique",
    "allergens_tags": ["en:celery"],
    "traces_tags": [],
    "additives_tags": ["en:e330"],
    "nutriscore_grade": "b",
    "nutriscore_score": 1,
    "nova_group": 3,
    "nutrient_levels": {"fat": "moderate", "salt": "moderate",
                        "saturated-fat": "low", "sugars": "moderate"},
    "labels": "Sans conservateur",
    "categories": "Plats préparés, Légumes préparés",
    "serving_size": "185 g",
}  # fmt: skip


def _online(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "food_lookup_online", True)

    def answer(request: httpx.Request) -> httpx.Response:
        assert "nova_group" in request.url.params["fields"]
        return httpx.Response(200, json={"status": 1, "product": PRODUCT})

    real = httpx.AsyncClient

    def fake(**kw: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(answer), **kw)

    monkeypatch.setattr(food_off.httpx, "AsyncClient", fake)


async def test_the_whole_product_page_is_kept(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _online(monkeypatch)
    found = await client.get(f"/api/v1/openfoodfacts/{CODE}", headers=auth)
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["per_100g"]["sodium_mg"] == 304  # as given, not from salt
    info = body["product_info"]
    assert (info["nutriscore"], info["nova"], info["fruits_veg_pct"]) == (
        "b",
        3,
        96.05,
    )
    assert info["fruits_veg_estimated"]  # « ~ », as on the page
    assert info["additives"] == ["E330"] and info["allergens"] == ["celery"]
    assert info["ingredients"].startswith("Aubergines 60 %")
    assert info["levels"]["salt"] == "moderate"
    assert info["other_100g"] == {"potassium": 0.21, "vitamin-c": 0.004}
    assert info["url"].endswith(CODE)
    sheet = {**body, "package_g": 185}
    saved = await client.post("/api/v1/foods", json=sheet, headers=auth)
    assert saved.status_code == 201, saved.text
    assert saved.json()["product_info"]["nova"] == 3


async def test_the_meal_reading_is_told_and_never_doubts_a_sheet(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _online(monkeypatch)
    body = (
        await client.get(f"/api/v1/openfoodfacts/{CODE}", headers=auth)
    ).json()
    await client.post("/api/v1/foods", json=body, headers=auth)

    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        assert '"nova": 3' in prompt and "E330" in prompt
        return {
            "items": [{"name": "Aubergines", "grams": 185}],
            "score": 8,
            "watch": [
                "Quantité de sodium dans les aubergines (vérifier l'étiquette"
                " réelle)",
                "Vérifier la composition sur l'emballage",
            ],
        }

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        "/api/v1/meals",
        data={"description": "petite boîte d'aubergines"},
        headers=auth,
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    read = await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    analysis = read.json()["analysis"]
    assert analysis["watch"] == ["Quantité de sodium dans les aubergines"]
    (box,) = analysis["items"]
    assert (box["grams"], box["sodium_mg"]) == (185, 562.4)


async def test_grams_written_are_kept_and_every_line_says_where_from(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        if "Juge ce repas" in prompt:
            assert "Tomates : 240 g (écrits par le patient" in prompt
            assert "Concombre : 150 g (estimés" in prompt
            return {"score": 8, "watch": [
                "Tomates : 240 g, de quoi bien s'hydrater",
                "Assez de sucres (10.6 g pour 185 g)",
                "Trop de sel : 557 mg dans le repas",
            ]}  # fmt: skip
        return {"items": [
            {"name": "Tomates", "grams": 400, "grams_from": "écrit"},
            {"name": "Concombre", "grams": 150},
        ]}  # fmt: skip

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        "/api/v1/meals",
        data={"description": "tomates 240 g, un demi concombre"},
        headers=auth,
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    read = await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    tomatoes, cucumber = read.json()["analysis"]["items"]
    assert (tomatoes["grams"], tomatoes["grams_from"]) == (240, "écrit")
    assert (cucumber["grams"], cucumber["grams_from"]) == (150, "IA")
    assert read.json()["analysis"]["watch"] == [
        "Tomates : 240 g, de quoi bien s'hydrater",  # a computed number
        "Assez de sucres",  # « (10.6 g pour 185 g) »: not computed, cut
    ]  # « 557 mg » outside brackets: the remark is dropped


async def test_a_count_said_beats_what_the_photo_shows(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        if "Juge ce repas" in prompt:
            assert "Tomate : 240 g (2 × 120 g : nombre dit" in prompt
            return {"score": 7}
        assert '"unit_g"' in prompt and "jamais la part vue" in prompt
        return {"items": [  # the grams a photo of a small salad shows
            {"name": "Tomate", "grams": 50, "unit_g": 120},
            {"name": "Concombre", "grams": 30, "unit_g": 300},
            {"name": "Comté", "grams": 20, "unit_g": 30},
            {"name": "Poulet", "grams": 100, "unit_g": 5000},  # implausible
            {"name": "Sel", "grams": 1, "unit_g": 2},  # no count said
        ]}  # fmt: skip

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    said = (
        "Entrée: 2 tomates, un demi concombre, une tranche de comté Plat: "
        "un filet de poulet cuit, sel"
    )
    made = await client.post("/api/v1/meals", data={"description": said},
                             headers=auth)  # fmt: skip
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    read = await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    lines = {i["name"]: i for i in read.json()["analysis"]["items"]}
    assert (lines["Tomate"]["grams"], lines["Tomate"]["units"]) == (
        240,
        "2 × 120 g",
    )
    assert lines["Concombre"]["grams"] == 150  # « un demi » × 300 g
    assert lines["Concombre"]["units"] == "0,5 × 300 g"
    assert (lines["Comté"]["grams"], lines["Comté"]["grams_from"]) == (
        30,
        "unités",
    )
    assert (lines["Poulet"]["grams"], lines["Poulet"]["grams_from"]) == (
        100,
        "IA",
    )
    assert lines["Sel"]["grams_from"] == "IA"
