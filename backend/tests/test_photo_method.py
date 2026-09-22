"""Photo method v2: quality, blinded rating, paired comparison, trend."""

from __future__ import annotations

import io
import math
from datetime import UTC, date, datetime, timedelta

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.models.photo import Photo, PhotoAnalysis
from app.models.user import User
from app.services import photo_compare, photo_method, photo_quality
from app.services import robust_stats as rs
from app.services.photo_pipeline import process
from httpx import AsyncClient
from PIL import Image, ImageDraw
from sqlalchemy import select


def _image(
    size: tuple[int, int] = (400, 600),
    color: tuple[int, int, int] = (120, 120, 120),
    *,
    sharp: bool = True,
) -> bytes:
    image = Image.new("RGB", size, color)
    if sharp:
        draw = ImageDraw.Draw(image)
        draw.ellipse((100, 120, 300, 500), fill=(220, 190, 160))
        for x in range(0, size[0], 20):
            draw.line((x, 0, x, 60), fill=(0, 0, 0), width=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def _upload(
    client: AsyncClient, auth: dict[str, str], day: str, data: bytes
) -> str:
    response = await client.post(
        "/api/v1/ingest/photo",
        files={"file": ("p.png", data, "image/png")},
        data={"angle": "face", "date_key": day},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_quality_flags_dark_blurry_and_tiny_images() -> None:
    report = photo_quality.assess(_image((100, 100), (10, 10, 10), sharp=False))
    assert report["ok"] is False
    assert "Photo trop sombre" in report["issues"]
    assert "Photo floue ou vide" in report["issues"]
    assert "Résolution trop faible" in report["issues"]
    assert photo_quality.assess(_image())["ok"] is True


def test_read_scores_clamps_and_ignores_junk() -> None:
    raw = {"waist_width": "12", "abdomen_volume": True}
    assert photo_method.read_scores(raw, "face") == {"waist_width": 10}
    assert photo_method.read_scores({"waist_width": math.nan}, "face") == {}
    deltas = photo_method.read_scores(
        {"flank_fat": -5, "back_rolls": 1.4}, "dos", low=-2, high=2
    )
    assert deltas == {"flank_fat": -2, "back_rolls": 1}


def test_prompts_are_angle_specific_and_blinded() -> None:
    prompt = photo_method.absolute_prompt("profil")
    assert "abdominal_protrusion" in prompt
    assert "side view" in prompt
    paired = photo_method.paired_prompt("face", vertical=True)
    assert "1 on top" in paired
    assert "older" not in paired
    assert "date" not in paired


def test_compose_stacks_wide_photos_vertically() -> None:
    wide = _image((800, 400))
    image, vertical = photo_compare.compose(wide, wide)
    assert vertical is True
    with Image.open(io.BytesIO(image)) as img:
        assert img.height > img.width
    tall = _image()
    _, vertical = photo_compare.compose(tall, tall)
    assert vertical is False


async def test_compare_cancels_position_bias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(
        [
            {"waist_width": 1, "abdomen_volume": 1},
            {"waist_width": -1, "abdomen_volume": 1},
        ]
    )

    async def fake_vision(prompt: str, image: bytes, **_: object) -> dict:
        return next(answers)

    monkeypatch.setattr(ollama, "vision_json", fake_vision)
    result = await photo_compare.compare("face", _image(), _image())
    assert result["deltas"] == {"waist_width": 1.0, "abdomen_volume": 0.0}
    assert result["consistent"] == {
        "waist_width": True,
        "abdomen_volume": False,
    }


async def test_pipeline_compares_with_baseline_and_week(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_vision(prompt: str, image: bytes, **_: object) -> dict:
        if "Anchored" in prompt:
            return {"waist_width": 6, "abdomen_volume": 5, "pose_ok": True}
        return {"waist_width": 0, "abdomen_volume": 0}

    monkeypatch.setattr(ollama, "vision_json", fake_vision)
    ids = [
        await _upload(client, auth, day, _image())
        for day in ("2026-01-01", "2026-01-24", "2026-01-31")
    ]
    async with SessionFactory() as session:
        for photo_id in ids:
            await process(session, photo_id)
    resp = await client.get(f"/api/v1/photos/{ids[2]}/analysis", headers=auth)
    comparisons = resp.json()["raw_output"]["comparisons"]
    assert [c["horizon"] for c in comparisons] == ["baseline", "7d"]
    assert comparisons[0]["ref_photo_id"] == ids[0]
    assert comparisons[1]["ref_photo_id"] == ids[1]
    assert resp.json()["comparison_ref"] == ids[0]


async def test_low_quality_photo_skips_the_ai(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(prompt: str, image: bytes, **_: object) -> dict:
        raise AssertionError("the AI must not rate an unusable photo")

    monkeypatch.setattr(ollama, "vision_json", boom)
    dark = _image((400, 600), (5, 5, 5), sharp=False)
    photo_id = await _upload(client, auth, "2026-02-01", dark)
    async with SessionFactory() as session:
        await process(session, photo_id)
    detail = await client.get(f"/api/v1/photos/{photo_id}", headers=auth)
    assert detail.json()["status"] == "low_quality"
    resp = await client.get(f"/api/v1/photos/{photo_id}/analysis", headers=auth)
    assert resp.json()["raw_output"]["quality"]["ok"] is False


def test_robust_stats_resist_outliers() -> None:
    start = date(2026, 1, 1)
    points = [(start + timedelta(days=i), 10.0 - 0.1 * i) for i in range(30)]
    points[10] = (points[10][0], 50.0)  # one absurd day
    slope = rs.theil_sen(points)
    assert slope is not None
    assert slope == pytest.approx(-0.1, abs=0.01)
    doubled = rs.daily_median([(start, 1.0), (start, 3.0)])
    assert doubled == [(start, 2.0)]
    smoothed = rs.rolling_median(points[:12], 7)
    assert smoothed[10][1] < 20
    assert rs.window_median(points, start, start) == 10.0
    assert rs.theil_sen(points[:1]) is None


async def _seed_scores(scores: list[float]) -> None:
    """Store one v2 analysis per day (every 3 days) for the face angle."""
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalars().first()
        assert user is not None
        start = date(2026, 3, 1)
        for i, score in enumerate(scores):
            day = start + timedelta(days=3 * i)
            photo = Photo(
                user_id=user.id,
                taken_at=datetime(day.year, day.month, day.day, tzinfo=UTC),
                date_key=day,
                original_path="x",
                normalized_path="x",
                angle="face",
                status="analyzed",
            )
            session.add(photo)
            await session.flush()
            session.add(_analysis(photo.id, score))
        await session.commit()


def _analysis(photo_id: str, score: float) -> PhotoAnalysis:
    return PhotoAnalysis(
        photo_id=photo_id,
        model="test",
        prompt_version="v2",
        raw_output={
            "method": "v2",
            "quality": {"ok": True},
            "scores": {"waist_width": score, "abdomen_volume": 5},
        },
    )


async def test_trend_detects_improvement(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _seed_scores([8, 8, 7, 7, 7, 6, 6, 5, 5, 4])
    resp = await client.get("/api/v1/evolution/trend", headers=auth)
    assert resp.status_code == 200
    angles = resp.json()["angles"]
    assert [a["angle"] for a in angles] == ["face", "profil", "dos"]
    face = angles[0]
    assert face["photos_valid"] == 10
    waist, volume = face["criteria"]
    assert waist["status"] == "improving"
    assert waist["slope_30d"] < 0
    assert waist["baseline_delta"] < 0
    assert volume["status"] == "stable"
    assert angles[1]["criteria"][0]["status"] == "insufficient"


async def test_trend_needs_enough_days(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _seed_scores([8, 4, 2])
    resp = await client.get("/api/v1/evolution/trend", headers=auth)
    waist = resp.json()["angles"][0]["criteria"][0]
    assert waist["status"] == "insufficient"
    assert waist["slope_30d"] is None
    assert waist["n"] == 3


async def test_reanalyze_all_is_accepted(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _upload(client, auth, "2026-02-02", _image())
    resp = await client.post("/api/v1/evolution/reanalyze-all", headers=auth)
    assert resp.status_code == 202
    assert isinstance(resp.json()["queued"], int)
