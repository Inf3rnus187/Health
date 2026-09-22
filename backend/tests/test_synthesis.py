"""AI clinical synthesis: facts, checked sentences, report and PDF."""

from __future__ import annotations

import re
from typing import Any

import pytest
from app.core import ollama
from app.services.synthesis_check import check, items
from httpx import AsyncClient

REPORTS = "/api/v1/reports"
MEAS = "/api/v1/measurements"
_FACTS = {
    "F1": "HbA1c : 6,62 % le 12/09/2026 ; précédent 7,4 % le 01/02/2025",
    "F2": "Stéatose hépatique (active)",
}


def test_a_sentence_must_cite_facts_holding_its_numbers() -> None:
    kept, _ = check("HbA1c passée de 7,4 % à 6,6 % [F1].", _FACTS)
    assert kept == {"text": "HbA1c passée de 7,4 % à 6,6 %.", "facts": ["F1"]}
    assert check("HbA1c à 6,6 %.", _FACTS) == (None, "aucun fait cité")
    assert check("HbA1c à 5,9 % [F1].", _FACTS)[1] == (
        "chiffre absent des faits cités : 5,9"
    )
    assert check("Voir [F9].", _FACTS)[1] == "référence inconnue F9"
    # A number must come from the facts the sentence cites.
    assert check("Stéatose, HbA1c 7,4 % [F2].", _FACTS)[0] is None
    # Codes (grades, analytes) too: S3 is not in the cited fact.
    assert check("Stéatose hépatique S3 [F2].", _FACTS)[1] == (
        "chiffre absent des faits cités : S3"
    )


def test_missing_data_needs_no_reference_but_no_number() -> None:
    assert check("Pas de bilan lipidique.", _FACTS, cite=False)[0]
    assert check("Pas de LDL depuis 2 ans.", _FACTS, cite=False)[0] is None
    assert items("Une phrase. Une autre !") == ["Une phrase.", "Une autre !"]


async def _seed(client: AsyncClient, auth: dict[str, str]) -> None:
    await client.post(
        "/api/v1/conditions", json={"name": "Diabète de type 2"}, headers=auth
    )
    items_ = [
        {"metric_key": "body.weight", "date_key": d, "value": v}
        for d, v in (("2026-06-01", 112), ("2026-09-20", 104.5))
    ]
    await client.post(MEAS, json={"items": items_}, headers=auth)


def _fact_id(prompt: str, needle: str) -> str:
    line = next(li for li in prompt.splitlines() if needle in li)
    found = re.match(r"\[(F\d+)\]", line)
    assert found is not None
    return found.group(1)


async def test_synthesis_report_keeps_only_proven_sentences(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed(client, auth)

    async def fake(prompt: str, **_: Any) -> dict[str, Any]:
        weight = _fact_id(prompt, "Dernier poids")
        cond = _fact_id(prompt, "Diabète de type 2")
        return {
            "synthese": [
                f"Diabète de type 2 déclaré [{cond}].",
                f"Dernier poids 104,5 kg [{weight}].",
                f"Poids de 98 kg [{weight}].",
            ],
            "donnees_manquantes": ["Pas d'HbA1c dans le dossier."],
        }

    monkeypatch.setattr(ollama, "text_json", fake)
    created = await client.post(
        REPORTS, json={"type": "synthesis"}, headers=auth
    )
    report = (
        await client.get(f"{REPORTS}/{created.json()['id']}", headers=auth)
    ).json()
    assert report["status"] == "ready"
    summary = report["summary"]
    assert summary["error"] is None
    assert [len(s["items"]) for s in summary["sections"]] == [2, 0, 0, 0, 1]
    assert summary["rejected"] == 1
    assert "98" in summary["rejected_items"][0]["reason"]
    sections = {f["section"] for f in summary["facts"]}
    assert {"Maladies déclarées", "Poids"} <= sections
    pdf = await client.get(f"{REPORTS}/{report['id']}/file", headers=auth)
    assert pdf.content[:4] == b"%PDF"


async def test_synthesis_reports_a_model_failure(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed(client, auth)

    async def down(prompt: str, **_: Any) -> dict[str, Any]:
        raise ConnectionError("ollama injoignable")

    monkeypatch.setattr(ollama, "text_json", down)
    created = await client.post(
        REPORTS, json={"type": "synthesis"}, headers=auth
    )
    report = created.json()
    assert report["status"] == "ready"
    assert report["summary"]["error"] == "ollama injoignable"
