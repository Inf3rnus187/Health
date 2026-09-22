"""Validated metabolic / liver markers (formulas, bands, API)."""

from __future__ import annotations

from datetime import date

import pytest
from app.core.db import SessionFactory
from app.models.user import User
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services import metabolic_scores as score
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec
from httpx import AsyncClient
from sqlalchemy import select


def test_formulas_match_published_definitions() -> None:
    assert score.whtr(100, 180) == pytest.approx(0.556, abs=0.001)
    assert score.bmi(90, 180) == pytest.approx(27.78, abs=0.01)
    assert score.fli(1.5, 30, 50, 100) == pytest.approx(78.7, abs=0.2)
    assert score.fib4(50, 30, 40, 250) == pytest.approx(0.949, abs=0.001)
    assert score.tyg(1.5, 1.0) == pytest.approx(8.923, abs=0.001)


async def _record_bio(values: dict[str, float]) -> None:
    """Store lab values the way the biology import does."""
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalars().first()
        assert user is not None
        cache = MetricCache()
        items = []
        for key, value in values.items():
            spec = MetricSpec(key, key, "biology", "float", None, "last")
            await cache.id_for(session, spec)
            items.append(
                MeasurementIn(
                    metric_key=key, date_key=date(2026, 9, 1), value=value
                )
            )
        await measure.record_batch(session, user.id, items, source="biology")
        await session.commit()


def _by_key(body: dict) -> dict[str, dict]:
    return {marker["key"]: marker for marker in body["markers"]}


async def test_markers_report_missing_inputs(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/evolution/markers", headers=auth)
    assert resp.status_code == 200
    whtr = _by_key(resp.json())["whtr"]
    assert whtr["level"] == "missing"
    assert whtr["missing"] == ["Tour de taille", "Taille"]


async def test_markers_from_profile_and_labs(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/measurements",
        json={
            "items": [
                {
                    "metric_key": "body.weight",
                    "date_key": "2026-09-01",
                    "value": 90,
                }
            ]
        },
        headers=auth,
    )
    await _record_bio(
        {
            "triglycerides": 1.5,
            "ggt": 50,
            "asat": 30,
            "alat": 40,
            "plaquettes": 250,
            "glycemie": 100,  # mg/dL → converted to 1.00 g/L
            "hba1c": 6.0,
        }
    )
    resp = await client.post(
        "/api/v1/evolution/profile",
        json={"waist_cm": 100, "height_cm": 180, "birth_year": 1980},
        headers=auth,
    )
    assert resp.status_code == 200
    markers = _by_key(resp.json())
    assert markers["whtr"]["value"] == pytest.approx(0.56)
    assert markers["whtr"]["level"] == "warn"
    assert markers["bmi"]["level"] == "warn"
    assert markers["fli"]["level"] in {"warn", "high"}
    assert markers["fib4"]["level"] == "ok"
    assert markers["hba1c"]["level"] == "warn"
    assert markers["glycemie"]["value"] == pytest.approx(1.0)
    assert markers["glycemie"]["level"] == "ok"
    assert markers["tyg"]["level"] == "high"
    assert resp.json()["profile"]["waist_cm"] == 100


async def test_profile_rejects_absurd_values(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/evolution/profile", json={"waist_cm": 5}, headers=auth
    )
    assert resp.status_code == 422
