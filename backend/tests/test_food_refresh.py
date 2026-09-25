"""A saved sheet reads its Open Food Facts page again, by its barcode."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models.food import Food
from app.services import food_off, food_refresh
from httpx import AsyncClient

CODE = "2001234567893"
FOODS = "/api/v1/foods"
PAGE = {
    "product_name_fr": "Aubergines cuisinées à la provençale",
    "brands": "Marque test",
    "product_quantity": 185,
    "nutriments": {"energy-kcal_100g": 83, "fat_100g": 5.2,
                   "salt_100g": 0.76, "sodium_100g": 0.304},
    "nutriscore_grade": "b",
    "nova_group": 3,
}  # fmt: skip
#: A sheet saved before: its 8 values without sodium, no details.
OLD = {
    "name": "Mes aubergines",
    "barcode": CODE,
    "portion_g": 185,
    "aliases": "ratatouille",
    "per_100g": {"energy_kcal": 83, "fat_g": 5.2},
}


def _online(monkeypatch: pytest.MonkeyPatch, page: dict[str, Any]) -> None:
    monkeypatch.setattr(get_settings(), "food_lookup_online", True)

    def answer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v2/product/{CODE}.json"
        return httpx.Response(200, json={"status": 1, "product": page})

    real = httpx.AsyncClient

    def fake(**kw: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(answer), **kw)

    monkeypatch.setattr(food_off.httpx, "AsyncClient", fake)


async def _sheet(client: AsyncClient, auth: dict[str, str], **kw: Any) -> str:
    made = await client.post(FOODS, json={**OLD, **kw}, headers=auth)
    assert made.status_code == 201, made.text
    return str(made.json()["id"])


async def test_one_sheet_is_completed_and_keeps_my_fields(
    client: AsyncClient,
    auth: dict[str, str],
    member: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    food = await _sheet(client, auth)
    offline = await client.post(f"{FOODS}/{food}/refresh", headers=auth)
    assert offline.status_code == 422  # lookup disabled: nothing leaves
    _online(monkeypatch, PAGE)
    theirs = await client.post(f"{FOODS}/{food}/refresh", headers=member)
    assert theirs.status_code == 404
    done = (await client.post(f"{FOODS}/{food}/refresh", headers=auth)).json()
    assert done["changed"] == [
        "sodium_mg",
        "product_info",
        "package_g",
        "brand",
    ]
    sheet = done["food"]
    assert sheet["per_100g"]["sodium_mg"] == 304
    assert (
        sheet["product_info"]["nova"] == 3
        and sheet["product_info"]["fetched_at"]
    )
    assert (sheet["name"], sheet["aliases"], sheet["portion_g"]) == (
        "Mes aubergines",
        "ratatouille",
        185,
    )
    again = (await client.post(f"{FOODS}/{food}/refresh", headers=auth)).json()
    assert again["changed"] == []
    none = await _sheet(client, auth, barcode="")
    no_code = await client.post(f"{FOODS}/{none}/refresh", headers=auth)
    assert no_code.status_code == 422


async def test_every_sheet_and_the_daily_job(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    await _sheet(client, auth)
    await _sheet(client, auth, barcode="")  # not looked up
    _online(monkeypatch, PAGE)
    done = (await client.post(f"{FOODS}/refresh", headers=auth)).json()
    assert [u["name"] for u in done["updated"]] == ["Mes aubergines"]
    assert (done["unchanged"], done["failed"], done["remaining"]) == (0, [], 0)
    monkeypatch.setattr(food_refresh, "_PAUSE_S", 0)
    async with SessionFactory() as session:
        assert await food_refresh.refresh_stale(session, 30) == 0  # fresh
        food = (
            await session.execute(
                Food.__table__.select().where(Food.barcode == CODE)
            )
        ).first()
        assert food is not None
        sheet = await session.get(Food, food.id)
        assert sheet is not None
        sheet.product_info = {
            **(sheet.product_info or {}),
            "fetched_at": "2026-01-02",
        }
        await session.commit()
        assert await food_refresh.refresh_stale(session, 0) == 0  # never
        assert await food_refresh.refresh_stale(session, 30) == 1
