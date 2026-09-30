"""The AI's remarks say what the reference table says."""

from __future__ import annotations

from typing import Any

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import meal_ai, meal_reference, meal_verdicts
from httpx import AsyncClient

#: A dinner: proteins above its part, sodium within, fibres below.
TOTALS = {"protein_g": 36, "sodium_mg": 657, "fiber_g": 3, "sugars_g": 5}


def _dinner() -> dict[str, Any] | None:
    return meal_reference.compare({"totals": TOTALS}, "dinner")


def _aligned(**judged: Any) -> dict[str, Any]:
    return meal_verdicts.align(judged, _dinner())


def test_the_model_is_told_each_verdict() -> None:
    lines = meal_verdicts.prompt_lines(_dinner())
    assert "Protéines 36 g : au-dessus de la part d'un dîner (15–20 g)." in (
        lines
    )
    assert "Sodium 657 mg : dans la part d'un dîner (600–800 mg)." in lines
    assert "Fibres 3 g : en dessous de la part d'un dîner (9–12 g)." in lines
    assert (
        meal_verdicts.prompt_lines(
            meal_reference.compare({"totals": TOTALS}, "snack")
        )
        == ""
    )  # no part for a snack: nothing to follow


def test_a_remark_against_its_verdict_becomes_the_codes() -> None:
    out = _aligned(
        positives=["Apport modéré en protéines.", "Riche en fibres"],
        watch=["Sodium élevé pour un dîner"],
    )
    assert out["positives"] == [
        "Protéines 36 g : au-dessus de la part d'un dîner (15–20 g).",
        "Fibres 3 g : en dessous de la part d'un dîner (9–12 g).",
    ]
    assert out["watch"] == [
        "Sodium 657 mg : dans la part d'un dîner (600–800 mg).",
    ]


@pytest.mark.parametrize(
    "remark",
    [
        "Riche en protéines",
        "Faible teneur en fibres",
        "Trop peu de fibres",
        "Pas trop salé",
        "Riche en protéines mais pauvre en fibres",
        "Il est important de limiter le sel",
        "Bonne source de protéines et de fibres",
        "Sucres et fibres faibles",
    ],
)
def test_a_remark_that_agrees_or_is_unclear_stays(remark: str) -> None:
    assert _aligned(positives=[remark])["positives"] == [remark]


def test_the_verdict_loses_only_its_wrong_part() -> None:
    out = _aligned(verdict="Repas équilibré, apport modéré en protéines")
    assert out["verdict"] == "Repas équilibré."
    kept = _aligned(verdict="Repas riche en protéines, un peu salé")
    assert kept["verdict"] == "Repas riche en protéines, un peu salé"


def test_a_snack_has_no_verdict_to_follow() -> None:
    snack = meal_reference.compare({"totals": TOTALS}, "snack")
    judged = {"positives": ["Apport modéré en protéines"]}
    assert meal_verdicts.align(judged, snack) == judged


async def test_the_analysis_follows_the_table(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any, **__: Any) -> bool:
        return False

    prompts: list[str] = []

    async def text(prompt: str, **_: Any) -> dict[str, Any]:
        prompts.append(prompt)
        if "Juge ce repas" in prompt:
            return {
                "score": 6,
                "verdict": "Dîner correct",
                "positives": ["Apport modéré en protéines"],
            }
        return {
            "items": [
                {
                    "name": "Poulet",
                    "grams": 150,
                    "protein_g": 36,
                    "carbs_g": 0,
                    "fat_g": 5,
                }
            ]
        }

    # fmt: skip

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    monkeypatch.setattr(ollama, "text_json", text)
    made = await client.post(
        "/api/v1/meals",
        data={"description": "Repas test", "meal_type": "dinner"},
        headers=auth,
    )
    async with SessionFactory() as session:
        await meal_ai.run(session, made.json()["id"])
    meal = (
        await client.get(f"/api/v1/meals/{made.json()['id']}", headers=auth)
    ).json()
    protein = meal["reference"]["rows"]["protein_g"]
    assert protein["verdict"] == "above"
    assert "au-dessus de la part d'un dîner" in prompts[-1]
    (remark,) = meal["analysis"]["positives"]
    assert remark.startswith("Protéines 36 g : au-dessus de la part d'un dîner")
