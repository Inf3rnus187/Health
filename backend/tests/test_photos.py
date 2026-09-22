"""Photo pipeline: upload, normalize, mocked Ollama analysis, serving."""

from __future__ import annotations

import io

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services.photo_pipeline import process
from httpx import AsyncClient
from PIL import Image, ImageDraw


def _figure(color: tuple[int, int, int] = (120, 120, 120)) -> Image.Image:
    """A 400x600 image with a sharp silhouette (passes quality control)."""
    image = Image.new("RGB", (400, 600), color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((120, 150, 280, 500), fill=(220, 190, 160))
    for x in range(0, 400, 20):
        draw.line((x, 0, x, 60), fill=(0, 0, 0), width=2)
    return image


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    _figure().save(buffer, format="PNG")
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


async def test_pipeline_rates_photo_with_method_v2(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_vision(prompt: str, image: bytes, **_: object) -> dict:
        return {"waist_width": 6, "abdomen_volume": "5", "confidence": 0.8}

    monkeypatch.setattr(ollama, "vision_json", fake_vision)
    photo_id = await _upload(client, auth, "2026-04-02")
    async with SessionFactory() as session:
        await process(session, photo_id)

    analysis = await client.get(
        f"/api/v1/photos/{photo_id}/analysis", headers=auth
    )
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["prompt_version"] == "v2"
    assert body["raw_output"]["quality"]["ok"] is True
    assert body["raw_output"]["scores"] == {
        "waist_width": 6,
        "abdomen_volume": 5,
    }
    assert body["raw_output"]["comparisons"] == []
    served = await client.get(f"/api/v1/photos/{photo_id}/file", headers=auth)
    assert served.status_code == 200


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


async def test_pipeline_survives_ai_failure(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If Ollama is down the photo stays viewable (status ai_failed)."""

    async def boom(prompt: str, image: bytes, **_: object) -> dict:
        raise RuntimeError("ollama unreachable")

    monkeypatch.setattr(ollama, "vision_json", boom)
    photo_id = await _upload(client, auth, "2026-04-03")
    async with SessionFactory() as session:
        await process(session, photo_id)

    detail = await client.get(f"/api/v1/photos/{photo_id}", headers=auth)
    assert detail.json()["status"] == "ai_failed"
    served = await client.get(f"/api/v1/photos/{photo_id}/file", headers=auth)
    assert served.status_code == 200


def _heic_bytes() -> bytes:
    import pillow_heif

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    _figure((30, 120, 200)).save(buffer, format="HEIF")
    return buffer.getvalue()


async def test_pipeline_handles_heic(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An Apple HEIC upload decodes, normalises and serves as an image."""

    async def fake_vision(prompt: str, image: bytes, **_: object) -> dict:
        return {"waist_width": 4, "abdomen_volume": 4}

    monkeypatch.setattr(ollama, "vision_json", fake_vision)
    resp = await client.post(
        "/api/v1/ingest/photo",
        files={"file": ("m.heic", _heic_bytes(), "image/heic")},
        data={"angle": "face"},
        headers=auth,
    )
    assert resp.status_code == 201
    photo_id = resp.json()["id"]
    async with SessionFactory() as session:
        await process(session, photo_id)
    detail = await client.get(f"/api/v1/photos/{photo_id}", headers=auth)
    assert detail.json()["status"] == "analyzed"
    served = await client.get(f"/api/v1/photos/{photo_id}/file", headers=auth)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")


async def test_reanalyze_requeues(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Re-analyze re-queues the pipeline for an existing photo."""
    photo_id = await _upload(client, auth, "2026-04-05")
    resp = await client.post(f"/api/v1/photos/{photo_id}/analyze", headers=auth)
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"


async def test_delete_one_photo(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Deleting a photo removes it from the list."""
    photo_id = await _upload(client, auth, "2026-04-06")
    resp = await client.delete(f"/api/v1/photos/{photo_id}", headers=auth)
    assert resp.status_code == 204
    listed = await client.get("/api/v1/photos", headers=auth)
    assert all(p["id"] != photo_id for p in listed.json())


async def test_delete_all_photos(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Deleting all clears the whole list."""
    await _upload(client, auth, "2026-04-07")
    await _upload(client, auth, "2026-04-08")
    resp = await client.delete("/api/v1/photos", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 2
    listed = await client.get("/api/v1/photos", headers=auth)
    assert listed.json() == []
