"""Reference values: the Ciqual table, quantities read, Open Food Facts."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from app.core import ollama
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.services import ciqual, food_off, meal_ai
from app.services.meal_quantity import grams_in
from httpx import AsyncClient

DINNER = (
    "Entrée: 2 tomates, un demi concombre, une tranche de comté Plat: 1 "
    "pavé de saumon nature 100g et pommes de terre rissolées nature  "
    "Aucune sauce aucune matière"
)


def test_the_table_is_read_with_the_anses_notation() -> None:
    assert len(ciqual.table()) > 3000
    tomato = ciqual.get("20385")
    assert tomato is not None and "Tomate" in tomato.name
    assert tomato.per_100g["energy_kcal"] == 19.2
    assert tomato.per_100g["fat_g"] == 0.25  # « < 0,5 »
    rice = ciqual.get("9104")
    assert rice is not None and rice.per_100g["sugars_g"] == 0.0  # traces
    assert ciqual.portion(tomato, 240)["energy_kcal"] == 46.1


def test_search_and_candidates_put_generic_foods_first() -> None:
    first = ciqual.search("tomate crue")[0]
    assert first.name.startswith("Tomate sans précision, crue")
    names = [r.name for r in ciqual.candidates([DINNER])]
    assert any(n.startswith("Comté") for n in names)
    assert any(n.startswith("Saumon, cuit") for n in names)
    assert any(n.startswith("Pomme de terre") for n in names)
    assert not any("matière" in n.lower() for n in names[:1])


def _food(**kw: Any) -> Any:
    base = {"aliases": "", "unit_g": None, "package_g": None, "brand": None,
            "unit_name": None}  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


@pytest.mark.parametrize(
    ("food", "text", "grams"),
    [
        (_food(name="Tomate", unit_g=120.0), DINNER, 240.0),
        (_food(name="Concombre", unit_g=300.0), DINNER, 150.0),
        (_food(name="Comté", unit_g=30.0), DINNER, 30.0),
        (_food(name="Pavé de saumon", aliases="saumon"), DINNER, 100.0),
        (_food(name="Pommes de terre rissolées"), DINNER, None),
        (_food(name="Riz", package_g=250.0), "½ sachet de riz", 125.0),
        (_food(name="Riz", package_g=250.0), "150 g de riz, poulet", 150.0),
        (_food(name="Riz", package_g=250.0), "riz et 2 œufs", None),
        (_food(name="Tomate", unit_g=120.0), "1/2 tomate", 60.0),
        (_food(name="Yaourt", package_g=125.0), "deux yaourts", 250.0),
    ],
)
def test_quantities_are_read_from_the_description(
    food: Any, text: str, grams: float | None
) -> None:
    assert grams_in(food, text) == grams


def _answer(salmon_grams: int) -> dict[str, Any]:
    wrong = {"protein_g": 99, "fat_g": 0, "source": "Ciqual"}
    return {
        "items": [
            {"name": "Saumon", "grams": salmon_grams, "ciqual": "25996",
             **wrong},
            {"name": "Tomates", "grams": 240, "ciqual": "20385"},
            {"name": "Sauce inconnue", "grams": 20, "ciqual": "99999999",
             "protein_g": 1, "carbs_g": 2, "fat_g": 3, "source": "Ciqual"},
            {"name": "Riz", "grams": 100, "ciqual": "9104",  # not offered
             "protein_g": 3, "carbs_g": 30, "fat_g": 1},
        ],
        "score": 7,
    }  # fmt: skip


async def test_a_meal_is_valued_from_the_table_whatever_the_model_says(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    prompts: list[str] = []

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        prompts.append(prompt)
        return _answer(100)

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    ids = []
    for words in (DINNER, DINNER.replace("saumon nature", "saumon cuit")):
        made = await client.post(
            "/api/v1/meals", data={"description": words}, headers=auth
        )
        ids.append(made.json()["id"])
        async with SessionFactory() as session:
            await meal_ai.run(session, ids[-1])
    assert "25996 : Saumon, cuit, sans précision (aliment moyen)" in prompts[0]
    first, second = [
        (await client.get(f"/api/v1/meals/{i}", headers=auth)).json()
        for i in ids
    ]
    items = first["analysis"]["items"]
    salmon, tomato, sauce, rice = items
    assert (salmon["source"], salmon["ciqual"]) == ("Ciqual", "25996")
    assert salmon["protein_g"] == 23.2 and salmon["energy_kcal"] == 205.0
    assert salmon["reference"] == (
        "Ciqual 2025 · Saumon, cuit, sans précision (aliment moyen)"
    )
    assert tomato["energy_kcal"] == 46.1
    assert "source" not in sauce  # an unknown code: the model's estimate
    assert "source" not in rice and "ciqual" not in rice  # not offered
    assert first["analysis"]["totals"] == second["analysis"]["totals"]


async def test_the_reference_search_route(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    res = await client.get(
        "/api/v1/ciqual", params={"q": "saumon vapeur"}, headers=auth
    )
    body = res.json()
    assert body["version"] == "Ciqual 2025"
    assert body["items"][0]["code"] == "26038"
    one = await client.get("/api/v1/ciqual/26038", headers=auth)
    assert one.json()["per_100g"]["protein_g"] == 23.0
    assert (await client.get("/api/v1/ciqual/1", headers=auth)).is_error


async def test_open_food_facts_only_when_allowed(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "/api/v1/openfoodfacts/3017620422003"
    off = await client.get(url, headers=auth)
    assert off.status_code == 422 and "FOOD_LOOKUP_ONLINE" in off.text
    monkeypatch.setattr(get_settings(), "food_lookup_online", True)
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        product = {
            "product_name_fr": "Riz méditerranéen",
            "brands": "Marque test, Autre",
            "product_quantity": "250",
            "nutriments": {"energy-kcal_100g": 150, "proteins_100g": 3.5,
                           "salt_100g": 0.8, "sugars_100g": 400},
        }  # fmt: skip
        return httpx.Response(200, json={"status": 1, "product": product})

    real = httpx.AsyncClient

    def fake(**kw: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(answer), **kw)

    monkeypatch.setattr(food_off.httpx, "AsyncClient", fake)
    found = (await client.get(url, headers=auth)).json()
    assert found["package_g"] == 250 and found["brand"] == "Marque test"
    assert found["per_100g"] == {
        "energy_kcal": 150, "protein_g": 3.5, "sodium_mg": 320.0,
    }  # fmt: skip
    assert found["source"] == "Open Food Facts · 3017620422003"
    assert sent[0].url.path == "/api/v2/product/3017620422003.json"
    assert "Authorization" not in sent[0].headers
    bad = await client.get("/api/v1/openfoodfacts/12ab", headers=auth)
    assert bad.status_code == 422
    assert json.loads(bad.text)
