"""A pack's barcode read on a photo: my food, or the product online."""

from __future__ import annotations

import io
from typing import Any

import httpx
import pytest
import zxingcpp
from app.core.config import get_settings
from app.services import food_off
from httpx import AsyncClient
from PIL import Image

SCAN = "/api/v1/foods/scan"
CODE = "3017620422003"


def _photo(code: str = CODE, turn: float = 12) -> bytes:
    """A camera-like shot: the code tilted on a coloured table, JPEG."""
    made = zxingcpp.create_barcode(code, zxingcpp.BarcodeFormat.EAN13)
    bars = Image.fromarray(zxingcpp.write_barcode_to_image(made, scale=4))
    shot = Image.new("RGB", (1400, 1000), (225, 210, 180))
    tilted = bars.convert("RGB").rotate(turn, expand=True, fillcolor="white")
    shot.paste(tilted, (350, 280))
    out = io.BytesIO()
    shot.save(out, format="JPEG", quality=75)
    return out.getvalue()


def _file(data: bytes) -> dict[str, Any]:
    return {"file": ("code.jpg", data, "image/jpeg")}


async def test_a_barcode_is_read_offline(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    res = await client.post(SCAN, files=_file(_photo(turn=190)), headers=auth)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["barcodes"] == [CODE]
    assert (body["food"], body["product"], body["online"]) == (
        None,
        None,
        False,
    )
    plain = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(plain, format="PNG")
    none = await client.post(SCAN, files=_file(plain.getvalue()), headers=auth)
    assert none.json()["barcodes"] == [] and none.json()["note"]
    bad = await client.post(SCAN, files=_file(b"not an image"), headers=auth)
    assert bad.status_code == 422


async def test_my_food_is_found_by_its_code_and_only_mine(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    food = await client.post(
        "/api/v1/foods",
        json={"name": "Riz méditerranéen", "barcode": CODE, "package_g": 250},
        headers=auth,
    )
    assert food.status_code == 201, food.text
    mine = (await client.post(SCAN, files=_file(_photo()), headers=auth)).json()
    assert mine["food"]["id"] == food.json()["id"]
    assert "path" not in str(mine["food"]["photos"])
    theirs = await client.post(SCAN, files=_file(_photo()), headers=member)
    assert theirs.json()["food"] is None  # never someone else's food


async def test_an_unknown_code_is_looked_up_when_allowed(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "food_lookup_online", True)

    def answer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v2/product/{CODE}.json"
        product = {"product_name": "Pâte à tartiner", "product_quantity": 400,
                   "nutriments": {"energy-kcal_100g": 539}}  # fmt: skip
        return httpx.Response(200, json={"status": 1, "product": product})

    real = httpx.AsyncClient

    def fake(**kw: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(answer), **kw)

    monkeypatch.setattr(food_off.httpx, "AsyncClient", fake)
    body = (await client.post(SCAN, files=_file(_photo()), headers=auth)).json()
    assert body["product"]["barcode"] == CODE
    assert body["product"]["package_g"] == 400
    assert body["product"]["per_100g"] == {"energy_kcal": 539}


async def test_a_shortcut_scans_with_its_token_in_the_url(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "scan", "scopes": ["write:measurements"]},
        headers=auth,
    )
    token = made.json()["token"]
    res = await client.post(f"{SCAN}?token={token}", files=_file(_photo()))
    assert res.status_code == 200, res.text
    assert res.json()["barcodes"] == [CODE]
    refused = await client.post(f"{SCAN}?token=nope", files=_file(_photo()))
    assert refused.status_code == 401
