"""Full HealthKit catalog: labels, category values, HAE names, backfill."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.db import SessionFactory
from app.models.base import new_uuid, utcnow
from app.models.health_raw import HealthSample
from app.models.metric import MetricDefinition
from app.models.user import User
from app.services import reconcile
from app.services.apple_health import hk_catalog
from app.services.apple_health.hk_values import category_value
from app.services.apple_health.metrics_cache import MetricCache
from app.services.apple_health.spec import MetricSpec, synth_spec
from app.services.apple_health.units import PERCENT_0_100, convert
from httpx import AsyncClient
from sqlalchemy import select

SYNC = "/api/v1/sync"
MEAS = "/api/v1/measurements"
_T0 = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)


def test_catalog_covers_the_sdk_and_speaks_french() -> None:
    protein = synth_spec("HKQuantityTypeIdentifierDietaryProtein", "g")
    assert protein == MetricSpec(
        "apple.dietary_protein", "Protéines", "nutrition", "float", "g", "sum"
    )
    headache = synth_spec("HKCategoryTypeIdentifierHeadache", None)
    assert (headache.label, headache.domain, headache.agg) == (
        "Maux de tête",
        "symptom",
        "max",
    )
    assert len(hk_catalog.TYPES) == 164  # 93 quantities + 71 categories


def test_category_events_become_numbers() -> None:
    sev = "HKCategoryTypeIdentifierHeadache"
    assert (
        category_value(sev, "HKCategoryValueSeverityModerate", None, None) == 2
    )
    assert (
        category_value(sev, "HKCategoryValueSeverityNotPresent", None, None)
        == 0
    )
    stand = "HKCategoryTypeIdentifierAppleStandHour"
    assert (
        category_value(stand, "HKCategoryValueAppleStandHourStood", None, None)
        == 1
    )
    assert (
        category_value(stand, "HKCategoryValueAppleStandHourIdle", None, None)
        == 0
    )
    mind = "HKCategoryTypeIdentifierMindfulSession"
    end = _T0.replace(minute=12)
    assert category_value(mind, "HKCategoryValueNotApplicable", _T0, end) == 12
    flow = "HKCategoryTypeIdentifierMenstrualFlow"
    assert (
        category_value(flow, "HKCategoryValueMenstrualFlowHeavy", None, None)
        == 3
    )
    ovu = "HKCategoryTypeIdentifierOvulationTestResult"
    raw = "HKCategoryValueOvulationTestResultIndeterminate"
    assert category_value(ovu, raw, None, None) is None
    event = "HKCategoryTypeIdentifierHighHeartRateEvent"
    assert (
        category_value(event, "HKCategoryValueNotApplicable", None, None) == 1
    )


def test_percent_scales() -> None:
    """Apple export: fraction → %; Health Auto Export: already 0-100."""
    assert convert(0.97, "%", "%") == pytest.approx(97)
    assert convert(0.9, PERCENT_0_100, "%") == 0.9


async def _token(client: AsyncClient, auth: dict[str, str]) -> str:
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "hae", "scopes": ["write:measurements"]},
        headers=auth,
    )
    return str(created.json()["token"])


def _metric(name: str, units: str, points: list[dict]) -> dict:
    return {"name": name, "units": units, "data": points}


async def test_hae_names_blood_pressure_sleep_and_percent(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    day = "2026-05-02 07:00:00 +0200"
    payload = {
        "data": {
            "metrics": [
                _metric(
                    "walking_running_distance",
                    "km",
                    [{"date": day, "qty": 3.2}],
                ),
                _metric(
                    "blood_pressure",
                    "mmHg",
                    [{"date": day, "systolic": 132, "diastolic": 84}],
                ),
                _metric(
                    "sleep_analysis",
                    "hr",
                    [{"date": day, "deep": 1.5, "rem": 1.0, "asleep": 6.5}],
                ),
                _metric(
                    "walking_asymmetry_percentage",
                    "%",
                    [{"date": day, "qty": 0.9}],
                ),
            ]
        }
    }
    token = await _token(client, auth)
    res = await client.post(f"{SYNC}/auto-export?token={token}", json=payload)
    assert res.status_code == 200
    expected = {
        "activity.distance": 3.2,
        "vitals.bp_systolic": 132,
        "vitals.bp_diastolic": 84,
        "sleep.deep": 90,
        "apple.walking_asymmetry_percentage": 0.9,
    }
    for key, value in expected.items():
        rows = await client.get(MEAS, params={"metric_key": key}, headers=auth)
        assert rows.json()[0]["value_num"] == pytest.approx(value), key


async def _user_id() -> str:
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalars().first()
        assert user is not None
        return user.id


async def test_reconcile_backfills_and_folds_legacy_keys() -> None:
    """Old category events get numbers; old HAE keys fold into canonical."""
    user_id = await _user_id()
    headache = synth_spec("HKCategoryTypeIdentifierHeadache", None)
    legacy = MetricSpec(
        "apple.walking_running_distance", "x", "apple", "float", "km", "avg"
    )
    async with SessionFactory() as session:
        head_id = await MetricCache().id_for(session, headache)
        old_id = await MetricCache().id_for(session, legacy)
        session.add_all(
            [
                _sample(
                    user_id, head_id, None, "HKCategoryValueSeveritySevere"
                ),
                _sample(user_id, old_id, 2.5, None),
            ]
        )
        await session.commit()
    async with SessionFactory() as session:
        report = await reconcile.run(session, user_id)
    assert report["categories"] == 1
    assert report["merged"]["apple.walking_running_distance"] in {1, -1}
    async with SessionFactory() as session:
        sample = await session.get(HealthSample, "s-" + head_id)
        assert sample is not None and sample.value_num == 3
        keys = set(
            (await session.execute(select(MetricDefinition.key))).scalars()
        )
        assert "apple.walking_running_distance" not in keys
        assert "activity.distance" in keys


def _sample(
    user_id: str, metric_id: str, value: float | None, text: str | None
) -> HealthSample:
    return HealthSample(
        id="s-" + metric_id if text else new_uuid(),
        user_id=user_id,
        metric_id=metric_id,
        start_at=_T0,
        value_num=value,
        value_text=text,
        unit="km" if value is not None else None,
        source="apple",
        created_at=utcnow(),
    )


async def test_every_domain_has_a_french_name(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    res = await client.get("/api/v1/catalog/domains", headers=auth)
    labels = res.json()
    assert labels["symptom"] == "Symptômes"
    assert labels["habit"].startswith("Habitudes")
    metrics = (await client.get("/api/v1/catalog", headers=auth)).json()
    domains = {m["domain"] for m in metrics}
    domains |= {t.domain for t in hk_catalog.TYPES.values()}
    assert domains <= set(labels)
