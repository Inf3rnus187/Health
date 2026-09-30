"""A meal's AI reading put off: photos and changes read with it, once."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.core.db import SessionFactory
from app.models.meal import Meal
from app.services import meal_ai
from httpx import AsyncClient
from PIL import Image

MEALS = "/api/v1/meals"


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """(meal id, planned time, delay) of each job handed to the worker."""
    seen: list[tuple[Any, ...]] = []

    async def worker(_: str, meal_id: str, stamp: Any, **kw: Any) -> bool:
        seen.append((meal_id, stamp, kw.get("defer")))
        return True

    monkeypatch.setattr(meal_ai, "enqueue", worker)
    return seen


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 120, 60)).save(out, "JPEG")
    return out.getvalue()


async def test_a_reading_put_off_waits_for_its_photos(
    client: AsyncClient, auth: dict[str, str], queued: list[tuple[Any, ...]]
) -> None:
    before = datetime.now(UTC)
    made = await client.post(
        MEALS,
        data={"description": "Repas test", "analysis_delay_min": "2"},
        headers=auth,
    )
    assert made.status_code == 201, made.text
    meal = made.json()
    after = datetime.fromisoformat(meal["analysis_after"])
    assert meal["analysis_status"] == "queued"
    assert timedelta(minutes=2) <= after - before < timedelta(minutes=3)
    assert queued == [(meal["id"], after.isoformat(), timedelta(minutes=2))]
    # a photo sent meanwhile: no reading now, the planned one reads it
    shot = {"file": ("plat.jpg", _jpeg(), "image/jpeg")}
    await client.post(f"{MEALS}/{meal['id']}/photos", files=shot, headers=auth)
    assert len(queued) == 1
    # « Relancer l'analyse »: at once, the planned job is replaced
    await client.post(f"{MEALS}/{meal['id']}/analyze", headers=auth)
    assert queued[-1][1:] == (None, None)
    read = (await client.get(f"{MEALS}/{meal['id']}", headers=auth)).json()
    assert read["analysis_after"] is None


@pytest.mark.parametrize("empty", ["", " ", "0"])
async def test_no_delay_reads_at_once(
    client: AsyncClient,
    auth: dict[str, str],
    queued: list[tuple[Any, ...]],
    empty: str,
) -> None:
    made = await client.post(
        MEALS,
        data={"description": "Repas test", "analysis_delay_min": empty},
        headers=auth,
    )
    assert made.json()["analysis_after"] is None
    assert queued == [(made.json()["id"], None, None)]


@pytest.mark.parametrize("wrong", ["-1", "61", "deux"])
async def test_a_wrong_delay_is_refused(
    client: AsyncClient,
    auth: dict[str, str],
    queued: list[tuple[Any, ...]],
    wrong: str,
) -> None:
    made = await client.post(
        MEALS,
        data={"description": "Repas test", "analysis_delay_min": wrong},
        headers=auth,
    )
    assert made.status_code == 422
    assert queued == []


async def test_a_job_whose_time_changed_does_nothing(
    client: AsyncClient, auth: dict[str, str], queued: list[tuple[Any, ...]]
) -> None:
    made = await client.post(
        MEALS,
        data={"description": "Repas test", "analysis_delay_min": "0,5"},
        headers=auth,
    )
    meal_id = made.json()["id"]
    old = datetime.now(UTC).isoformat()  # not the time planned
    async with SessionFactory() as session:
        await meal_ai.run(session, meal_id, old)
        meal = await session.get(Meal, meal_id)
        assert meal is not None and meal.analysis_status == "queued"


async def test_a_meal_put_off_stays_its_users(
    client: AsyncClient,
    auth: dict[str, str],
    member: dict[str, str],
    queued: list[tuple[Any, ...]],
) -> None:
    made = await client.post(
        MEALS,
        data={"description": "Repas test", "analysis_delay_min": "2"},
        headers=auth,
    )
    meal_id = made.json()["id"]
    theirs = await client.post(f"{MEALS}/{meal_id}/analyze", headers=member)
    assert theirs.status_code == 404
    assert (
        await client.get(f"{MEALS}/{meal_id}", headers=member)
    ).status_code == 404
    assert len(queued) == 1
