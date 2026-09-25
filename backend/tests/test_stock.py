"""The stock of « Mes aliments »: bought, thrown, counted — and eaten."""

from __future__ import annotations

from typing import Any

from app.core.db import SessionFactory
from app.models.meal import Meal
from httpx import AsyncClient

STOCK = "/api/v1/stock"
BOX = {
    "name": "Aubergines cuisinées à la provençale",
    "brand": "Marque test",
    "package_g": 185,
    "portion_g": 185,
    "barcode": "2001234567893",
    "per_100g": {"energy_kcal": 83},
}


async def _food(client: AsyncClient, auth: dict[str, str], **kw: Any) -> str:
    made = await client.post("/api/v1/foods", json={**BOX, **kw}, headers=auth)
    assert made.status_code == 201, made.text
    return str(made.json()["id"])


async def _meal(
    client: AsyncClient,
    auth: dict[str, str],
    food_id: str,
    grams: float,
    **kw: Any,
) -> str:
    """A meal whose reading used ``grams`` of the food's sheet."""
    made = await client.post(
        "/api/v1/meals",
        data={"description": "aubergines", "eaten_at": kw.pop("at", "")},
        headers=auth,
    )
    assert made.status_code == 201, made.text
    async with SessionFactory() as session:
        meal = await session.get(Meal, made.json()["id"])
        assert meal is not None
        line = {"name": "x", "food_id": food_id, "grams": grams,
                "source": "étiquette"}  # fmt: skip
        meal.analysis, meal.analysis_status = {"items": [line]}, "done"
        meal.price = kw.get("price")
        await session.commit()
    return str(made.json()["id"])


async def _level(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    body = (await client.get(STOCK, headers=auth)).json()
    return dict(body["foods"][0]) if body["foods"] else {}


async def test_bought_minus_eaten_and_a_deleted_meal_gives_back(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    food = await _food(client, auth)
    first = {"barcode": "2001234567893", "packs": 3, "at": "2026-09-20T10:00"}
    bought = await client.post(STOCK, json=first, headers=auth)
    assert bought.status_code == 201, bought.text
    assert bought.json()["move"]["said"] == "3 × 185 g"
    assert bought.json()["level"]["grams"] == 555
    meal = await _meal(client, auth, food, 185, at="2026-09-21T20:00")
    await _meal(client, auth, food, 185, at="2026-09-19T20:00")  # before
    await _meal(client, auth, food, 185, at="2026-09-21T21:00", price=12.5)
    level = await _level(client, auth)
    assert (level["grams"], level["packs"], level["eaten_g"]) == (370, 2, 185)
    await client.delete(f"/api/v1/meals/{meal}", headers=auth)
    assert (await _level(client, auth))["grams"] == 555


async def test_a_count_resets_and_a_loss_takes_out(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    food = await _food(client, auth)
    first = {"food": "auberg", "packs": 4, "at": "2026-09-20T10:00"}
    await client.post(STOCK, json=first, headers=auth)
    await _meal(client, auth, food, 185, at="2026-09-21T12:00")
    counted = await client.post(
        STOCK, json={"food_id": food, "kind": "count", "packs": 1,
                     "at": "2026-09-22T09:00"}, headers=auth,
    )  # fmt: skip
    assert counted.json()["level"]["grams"] == 185  # the meal is in it
    thrown = await client.post(
        STOCK, json={"food_id": food, "kind": "out", "grams": 50}, headers=auth
    )
    assert thrown.json()["level"]["grams"] == 135
    await _meal(client, auth, food, 185)  # more than is left
    level = await _level(client, auth)
    assert (level["grams"], level["missing"]) == (0, 50)
    history = await client.get(f"{STOCK}/{food}/moves", headers=auth)
    kinds = [m["kind"] for m in history.json()["moves"]]
    counted_at = history.json()["moves"][1]["at"]
    assert counted_at.endswith(("Z", "+00:00"))  # never a naive time
    assert kinds == ["out", "count", "purchase"]
    assert len(history.json()["eaten"]) == 2
    gone = await client.delete(
        f"{STOCK}/moves/{history.json()['moves'][0]['id']}", headers=auth
    )
    assert gone.status_code == 200


async def test_sizes_names_and_quantities_are_never_guessed(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _food(client, auth)
    await _food(client, auth, package_g=750, barcode="2009876543219")
    two = await client.post(STOCK, json={"food": "aubergines"}, headers=auth)
    assert (
        two.status_code == 422 and "185 g" in two.text and "750 g" in two.text
    )
    big = await client.post(
        STOCK, json={"barcode": "2009876543219"}, headers=auth
    )
    assert big.json()["level"]["grams"] == 750  # one pack by default
    none = await client.post(STOCK, json={"food": "saumon"}, headers=auth)
    assert none.status_code == 404
    loose = await _food(client, auth, name="Tomate", package_g=None,
                        barcode="", unit_name="tomate", unit_g=120)  # fmt: skip
    units = await client.post(STOCK, json={"food_id": loose, "units": 6},
                              headers=auth)  # fmt: skip
    assert units.json()["move"]["said"] == "6 × tomate"
    assert units.json()["level"]["units"] == 6
    packs = await client.post(STOCK, json={"food_id": loose}, headers=auth)
    assert packs.status_code == 422  # no package weight: say how much


async def test_only_my_foods_and_a_shortcut_token(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    food = await _food(client, auth)
    theirs = await client.post(STOCK, json={"food_id": food}, headers=member)
    assert theirs.status_code == 404
    by_code = await client.post(
        STOCK, json={"barcode": "2001234567893"}, headers=member
    )
    assert by_code.status_code == 404
    assert (
        await client.get(f"{STOCK}/{food}/moves", headers=member)
    ).status_code == 404
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "courses", "scopes": ["write:measurements"]},
        headers=auth,
    )
    token = made.json()["token"]
    scanned = await client.post(
        f"{STOCK}?token={token}", json={"barcode": "2001234567893"}
    )
    assert (
        scanned.status_code == 201
        and scanned.json()["move"]["source"] == "raccourci"
    )
    move = scanned.json()["move"]["id"]
    assert (await client.get(STOCK, headers=member)).json()["foods"] == []
    denied = await client.delete(f"{STOCK}/moves/{move}", headers=member)
    assert denied.status_code == 404
