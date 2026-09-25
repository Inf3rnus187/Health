"""« Mes aliments » found by the few words a meal uses for them."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import meal_ai
from app.services.food_match import fits, named
from app.services.meal_quantity import grams_in, read, written
from httpx import AsyncClient

BREAKFAST = (
    "2 tomates, un demi concombre, petite boîte d'aubergines, "
    "un pavé de saumon"
)


def _food(name: str, **kw: Any) -> Any:
    base = {"brand": None, "aliases": "", "unit_name": None, "unit_g": None,
            "package_g": None, "portion_g": None}  # fmt: skip
    return SimpleNamespace(id=kw.pop("id", name), name=name, **{**base, **kw})


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


SMALL = _food(
    "Aubergines cuisinées à la provençale", id="small", brand="Marque test",
    package_g=185.0, portion_g=185.0,
)  # fmt: skip
BIG = _food(
    "Aubergines cuisinées à la provençale", id="big", brand="Marque test",
    package_g=750.0, portion_g=187.5,
)  # fmt: skip


@pytest.mark.parametrize(
    ("text", "found", "grams"),
    [
        ("petite boîte d'aubergines", SMALL, 185.0),  # the usual: the box
        ("grosse boîte d'aubergines", BIG, 187.5),  # the usual: ¼
        ("un quart de la grosse boîte d'aubergines", BIG, 187.5),
        ("la moitié de la grosse boîte d'aubergines", BIG, 375.0),
        ("boîte de 750 g d'aubergines", BIG, 750.0),
        ("boîte d'aubergines", None, None),  # which size? neither
    ],
)
def test_the_size_said_picks_the_sheet(
    text: str, found: Any, grams: float | None
) -> None:
    assert named([SMALL, BIG, SALMON], text) == ([found] if found else [])
    if found is not None:
        assert grams_in(found, text) == grams


def test_the_grams_follow_the_words_used() -> None:
    assert grams_in(SALMON, BREAKFAST) == 100.0  # one pavé
    assert grams_in(EGGPLANT, BREAKFAST) is None  # box weight unknown
    box = _food("Aubergines cuisinées à la provençale", package_g=185.0)
    assert grams_in(box, BREAKFAST) == 185.0  # the box
    assert grams_in(SALMON, "2 pavés de saumon") == 200.0


def test_written_grams_are_read_past_cuit_and_nature() -> None:
    salmon = _food(
        "Saumon sauvage rose", aliases="saumon", unit_name="Pavé", unit_g=100.0
    )
    said = (
        "Entrée: 2 tomates, un demi concombre, une tranche de comté Plat: "
        "1 pavé saumon cuit nature {}g et pommes de terres rissolées nature"
    )
    assert read(salmon, said.format(100)) == (100.0, "écrit")
    assert read(salmon, said.format(150)) == (150.0, "écrit")  # not 1 pavé
    line = written([{"name": "Tomates", "unit_g": 150}], "tomates crues 240 g")
    assert (line[0]["grams"], line[0]["grams_from"]) == (240.0, "écrit")


def test_a_line_of_the_model_is_recognised() -> None:
    assert fits(SALMON, "Pavé de saumon grillé")
    assert fits(EGGPLANT, "Aubergines à la provençale (Marque test)")
    assert not fits(SALMON, "Saumon fumé")
    assert not fits(CHICKEN, "Blanc de poulet")


async def _sheet(client: AsyncClient, auth: dict[str, str], **kw: Any) -> str:
    made = await client.post("/api/v1/foods", json=kw, headers=auth)
    assert made.status_code == 201, made.text
    return str(made.json()["id"])


async def test_the_breakfast_is_valued_from_my_sheets(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    salmon = await _sheet(
        client, auth, name="Saumon sauvage rose", unit_name="Pavé",
        unit_g=100, package_g=200,
        per_100g={"energy_kcal": 127, "protein_g": 20.5, "fat_g": 4.4},
    )  # fmt: skip
    for grams, usual in ((185, 185), (750, 187.5)):
        await _sheet(
            client, auth, name="Aubergines cuisinées à la provençale",
            brand="Marque test", package_g=grams, portion_g=usual,
            per_100g={"energy_kcal": 83},
        )  # fmt: skip

    async def no_worker(*_: Any) -> bool:
        return False

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        assert "Saumon sauvage rose" in prompt and "· 185 g" in prompt
        assert "750 g" not in prompt  # the big box is not in this meal
        return {"items": [
            {"name": "Saumon", "grams": 100, "ciqual": "26039"},
            {"name": "Tomates", "grams": 240},
            {"name": "Saumon sauvage rose", "grams": 150, "food_id": salmon},
            {"name": "Aubergine", "grams": 100, "ciqual": "20007"},
        ]}  # fmt: skip

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        "/api/v1/meals", data={"description": BREAKFAST}, headers=auth
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    meal = await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    fish, tomatoes, box = meal.json()["analysis"]["items"]
    assert (fish["name"], fish["grams"], fish["source"]) == (
        "Saumon sauvage rose · 200 g",
        100,
        "étiquette",
    )
    assert fish["energy_kcal"] == 127 and tomatoes["name"] == "Tomates"
    assert (
        box["name"]
        == "Aubergines cuisinées à la provençale · Marque test · 185 g"
    )
    assert (box["grams"], box["energy_kcal"]) == (185, 153.6)
