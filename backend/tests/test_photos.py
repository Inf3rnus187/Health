"""Photo pipeline: upload, normalize, mocked Ollama analysis, serving."""

from __future__ import annotations

import io

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services.photo_pipeline import process
from httpx import AsyncClient
from PIL import Image


def _png_bytes() -> bytes:
    image = Image.new("RGB", (64, 96), (120, 120, 120))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def _upload(client: AsyncClient, auth: dict[str, str], day: str) -> str:
    response = await client.post(
        "/api/v1/ingest/photo",
        files={"file": ("front.png", _png_bytes(), "image/png")},
        data={"angle": "face", "date_key": day},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_upload_creates_received_photo(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    photo_id = await _upload(client, auth, "2026-04-01")
    detail = await client.get(f"/api/v1/photos/{photo_id}", headers=auth)
    assert detail.json()["status"] == "received"


async def test_rejects_non_image(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/ingest/photo",
        files={"file": ("x.txt", b"hello", "text/plain")},
        data={"angle": "face"},
        headers=auth,
    )
    assert response.status_code == 422


async def test_pipeline_analyses_and_injects_metric(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_vision(prompt: str, image: bytes, **_: object) -> dict:
        return {"silhouette_change": "stable", "waist_estimate": "medium"}

    monkeypatch.setattr(ollama, "vision_json", fake_vision)
    photo_id = await _upload(client, auth, "2026-04-02")
    async with SessionFactory() as session:
        await process(session, photo_id)

    analysis = await client.get(
        f"/api/v1/photos/{photo_id}/analysis", headers=auth
    )
    assert analysis.status_code == 200
    assert analysis.json()["raw_output"]["waist_estimate"] == "medium"
    served = await client.get(f"/api/v1/photos/{photo_id}/file", headers=auth)
    assert served.status_code == 200
    measured = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "ai.silhouette_change"},
        headers=auth,
    )
    assert measured.json()[0]["value"] == "stable"


async def test_compare_two_photos(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    first = await _upload(client, auth, "2026-04-01")
    second = await _upload(client, auth, "2026-04-08")
    response = await client.get(
        "/api/v1/photos/compare",
        params={"from": first, "to": second},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["from_photo"]["id"] == first
    assert response.json()["to_photo"]["id"] == second
