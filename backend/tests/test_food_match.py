"""« Mes aliments » found by the few words a meal uses for them."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import meal_ai
from app.services.food_match import fits, named
from app.services.meal_quantity import grams_in
from httpx import AsyncClient

BREAKFAST = (
    "2 tomates, un demi concombre, petite boîte d'aubergines, "
    "un pavé de saumon"
)


def _food(name: str, **kw: Any) -> Any:
    base = {"brand": None, "aliases": "", "unit_name": None, "unit_g": None,
            "package_g": None}  # fmt: skip
    return SimpleNamespace(id=name, name=name, **{**base, **kw})


EGGPLANT = _food("Aubergines cuisinées à la provençale", brand="Marque test")
SALMON = _food(
    "Saumon sauvage rose", unit_name="Pavé", unit_g=100.0, package_g=200.0
)
CHICKEN = _food("Poulet basquaise", package_g=900.0)
RISOTTO = _food("Risotto au poulet", brand="Marque test", package_g=908.0)
POTATOES = _food("Pommes rissolées", package_g=1000.0)
RICE = _food("Riz à la méditerranéenne", package_g=250.0)
MINE = [EGGPLANT, SALMON, CHICKEN, RISOTTO, POTATOES, RICE]


@pytest.mark.parametrize(
    ("text", "found"),
    [
        (BREAKFAST, [EGGPLANT, SALMON]),
        ("poulet basquaise et riz", [CHICKEN]),
        ("un risotto au poulet", [RISOTTO]),
        ("sachet de riz", [RICE]),
        ("risotto Marque test", [RISOTTO]),
        ("filet de poulet grillé", []),  # « filet » is not its word
        ("2 pommes", []),  # nothing confirms the rissolées
        ("sachet de riz basmati", []),  # « basmati » is another rice
        ("une barquette de poulet", []),  # two foods fit: neither
        ("tomate, pavé de boeuf", []),
    ],
)
def test_a_part_names_a_food_only_when_nothing_contradicts(
    text: str, found: list[Any]
) -> None:
    assert named(MINE, text) == found


def test_the_grams_follow_the_words_used() -> None:
    assert grams_in(SALMON, BREAKFAST) == 100.0  # one pavé
    assert grams_in(EGGPLANT, BREAKFAST) is None  # box weight unknown
    box = _food("Aubergines cuisinées à la provençale", package_g=185.0)
    assert grams_in(box, BREAKFAST) == 185.0  # the box
    assert grams_in(SALMON, "2 pavés de saumon") == 200.0


def test_a_line_of_the_model_is_recognised() -> None:
    assert fits(SALMON, "Pavé de saumon grillé")
    assert fits(EGGPLANT, "Aubergines à la provençale (Marque test)")
    assert not fits(SALMON, "Saumon fumé")
    assert not fits(CHICKEN, "Blanc de poulet")


async def test_the_breakfast_is_valued_from_my_sheets(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    per_100g = {"energy_kcal": 127, "protein_g": 20.5, "fat_g": 4.4}
    sheet = {"name": "Saumon sauvage rose", "unit_name": "Pavé",
             "unit_g": 100, "package_g": 200, "per_100g": per_100g}  # fmt: skip
    salmon = (
        await client.post("/api/v1/foods", json=sheet, headers=auth)
    ).json()

    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        assert "Saumon sauvage rose" in prompt
        ciqual = {"name": "Saumon", "grams": 100, "ciqual": "26039"}
        mine = {"name": "Saumon sauvage rose", "grams": 150,
                "food_id": salmon["id"]}  # fmt: skip
        return {"items": [ciqual, {"name": "Tomates", "grams": 240}, mine]}

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        "/api/v1/meals", data={"description": BREAKFAST}, headers=auth
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    meal = await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    items = meal.json()["analysis"]["items"]
    assert [i["name"] for i in items] == ["Saumon sauvage rose", "Tomates"]
    assert (items[0]["source"], items[0]["grams"]) == ("étiquette", 100)
    assert items[0]["energy_kcal"] == 127
