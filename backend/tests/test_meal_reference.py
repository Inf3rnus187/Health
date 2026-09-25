"""A meal against official daily references, by meal type."""

from __future__ import annotations

from typing import Any

import pytest
from app.core.db import SessionFactory
from app.models.meal import Meal
from app.services import meal_ai, meal_reference
from httpx import AsyncClient

MEALS = "/api/v1/meals"
REFERENCES = "/api/v1/nutrition/references"
TOTALS = {
    "grams": 700,
    "energy_kcal": 363,
    "protein_g": 38.4,
    "carbs_g": 19.9,
    "sugars_g": 12.7,
    "fat_g": 14.2,
    "sat_fat_g": 2.7,
    "fiber_g": 7.4,
    "sodium_mg": 657.1,
}


def test_a_dinner_is_set_against_its_part_of_the_day() -> None:
    out = meal_reference.compare({"totals": TOTALS}, "dinner")
    assert out is not None and out["share_pct"] == [30, 40]
    energy, sodium = out["rows"]["energy_kcal"], out["rows"]["sodium_mg"]
    assert (energy["low"], energy["high"]) == (600, 800)  # 2 000 kcal (UE)
    assert energy["day_pct"] == 18 and energy["verdict"] == "below"
    assert (sodium["low"], sodium["high"], sodium["source"]) == (
        600,
        800,
        "OMS",
    )
    assert sodium["kind"] == "limit" and sodium["verdict"] == "within"
    protein = out["rows"]["protein_g"]
    assert (protein["high"], protein["verdict"]) == (20, "above")  # 50 g
    fiber = out["rows"]["fiber_g"]
    assert (fiber["low"], fiber["kind"], fiber["verdict"]) == (
        9,
        "target",
        "below",
    )


def test_a_breakfast_has_its_part_and_a_snack_only_the_day() -> None:
    breakfast = meal_reference.compare({"totals": TOTALS}, "breakfast")
    assert breakfast is not None
    assert breakfast["rows"]["protein_g"]["low"] == 7.5  # 15 % of 50 g
    snack = meal_reference.compare({"totals": TOTALS}, "snack")
    assert snack is not None and snack["share_pct"] is None
    assert snack["rows"]["sodium_mg"] == {
        "day": 2000,
        "unit": "mg",
        "kind": "limit",
        "source": "OMS",
        "day_pct": 33,
    }


@pytest.mark.parametrize(
    "analysis", [None, {"error": "Ollama"}, {"totals": "?"}]
)
def test_no_totals_no_reference(analysis: Any) -> None:
    assert meal_reference.compare(analysis, "dinner") is None


async def test_a_meal_carries_its_reference_and_stays_its_users(
    client: AsyncClient,
    auth: dict[str, str],
    member: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    made = await client.post(
        MEALS,
        data={"meal_type": "dinner", "description": "Traitement A test"},
        headers=auth,
    )
    meal_id = made.json()["id"]
    assert made.json()["reference"] is None  # not read yet
    async with SessionFactory() as session:
        meal = await session.get(Meal, meal_id)
        assert meal is not None
        meal.analysis, meal.analysis_status = {"totals": TOTALS}, "done"
        await session.commit()
    read = (await client.get(f"{MEALS}/{meal_id}", headers=auth)).json()
    assert read["reference"]["rows"]["sodium_mg"]["verdict"] == "within"
    changed = await client.put(
        f"{MEALS}/{meal_id}", json={"meal_type": "snack"}, headers=auth
    )
    assert changed.json()["reference"]["share_pct"] is None
    theirs = await client.get(f"{MEALS}/{meal_id}", headers=member)
    assert theirs.status_code == 404


async def test_the_references_and_their_sources(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    mine = (await client.get(REFERENCES, headers=auth)).json()
    assert mine["daily"]["sodium_mg"] == {
        "value": 2000,
        "unit": "mg",
        "kind": "limit",
        "source": "OMS",
    }
    assert mine["share_pct"]["dinner"] == [30, 40]
    assert set(mine["sources"]) == {"UE", "ANSES", "OMS", "repas"}
    assert (await client.get(REFERENCES, headers=member)).json() == mine
    assert (await client.get(REFERENCES)).status_code == 401
