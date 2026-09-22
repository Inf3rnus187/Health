"""AI reading of medical documents: exact parsers + grounded AI values."""

from __future__ import annotations

from datetime import date

import pytest
from app.core import ollama
from app.core.db import SessionFactory
from app.services import document_ai, fibroscan
from app.services import document_grounding as grounding
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from httpx import AsyncClient

_UNITS = {"bio.hba1c": "%", "liver.cap": "dB/m"}
_TEXT = "Compte rendu du 12/09/2026. HbA1c a 7,9 % ce jour."


def _pdf(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def test_grounding_keeps_only_proven_values() -> None:
    items = [
        {"key": "bio.hba1c", "value": 7.9, "unit": "%", "date": "2026-09-12"},
        {"key": "bio.hba1c", "value": 8.4, "unit": "%", "date": "2026-09-12"},
        {"key": "bio.hba1c", "value": 7.9, "unit": "%", "date": "2025-01-01"},
        {
            "key": "bio.hba1c",
            "value": 7.9,
            "unit": "mmol/mol",
            "date": "2026-09-12",
        },
        {"key": "bio.unknown", "value": 7.9, "unit": "%", "date": "2026-09-12"},
        "junk",
    ]
    accepted, rejected = grounding.ground(items, _TEXT, _UNITS)
    assert accepted == [grounding.Grounded("bio.hba1c", 7.9, date(2026, 9, 12))]
    assert rejected == 5
    assert grounding.ground("not a list", _TEXT, _UNITS) == ([], 0)


def test_fibroscan_reader() -> None:
    text = (
        "Rapport FibroScan\nDate d'examen : 15/09/2026\n"
        "E mediane 5,2 kPa IQR/med 12 %\nCAP median 356 dB/m\n"
    )
    found = fibroscan.parse(text, date(2026, 1, 1))
    assert found == [
        ("liver.cap", 356.0, date(2026, 9, 15)),
        ("liver.lsm", 5.2, date(2026, 9, 15)),
    ]
    assert fibroscan.parse("no elastography here", date(2026, 1, 1)) == []


async def _upload(
    client: AsyncClient, auth: dict[str, str], lines: list[str], kind: str
) -> str:
    resp = await client.post(
        "/api/v1/medical/documents",
        files={"file": ("doc.pdf", _pdf(lines), "application/pdf")},
        data={"kind": kind},
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_fibroscan_document_feeds_the_markers(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake(prompt: str, model: str, **_: object) -> dict:
        return {"document_type": "fibroscan", "summary": "Steatose S3."}

    monkeypatch.setattr(ollama, "generate_json", fake)
    lines = [
        "Rapport FibroScan - Date d'examen : 15/09/2026",
        "E mediane 5,2 kPa IQR/med 12 %",
        "CAP median 356 dB/m",
    ]
    doc_id = await _upload(client, auth, lines, "autre")
    async with SessionFactory() as session:
        await document_ai.run(session, doc_id)
    docs = (await client.get("/api/v1/medical/documents", headers=auth)).json()
    doc = next(d for d in docs if d["id"] == doc_id)
    assert doc["analysis_status"] == "done"
    assert doc["kind"] == "imagerie"
    assert doc["doc_date"] == "2026-09-15"
    assert doc["analysis"]["summary"] == "Steatose S3."
    assert {v["key"] for v in doc["analysis"]["values"]} == {
        "liver.cap",
        "liver.lsm",
    }
    markers = (
        await client.get("/api/v1/evolution/markers", headers=auth)
    ).json()
    cap = next(m for m in markers["markers"] if m["key"] == "cap")
    assert cap["value"] == 356
    assert cap["date"] == "2026-09-15"


async def test_ai_values_are_grounded_before_storage(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake(prompt: str, model: str, **_: object) -> dict:
        assert "bio.hba1c" in prompt
        return {
            "document_type": "compte_rendu",
            "values": [
                {
                    "key": "bio.hba1c",
                    "value": 7.9,
                    "unit": "%",
                    "date": "2026-09-12",
                },
                {
                    "key": "bio.ggt",
                    "value": 88,
                    "unit": "U/L",
                    "date": "2026-09-12",
                },
            ],
        }

    monkeypatch.setattr(ollama, "generate_json", fake)
    doc_id = await _upload(client, auth, [_TEXT], "compte_rendu")
    async with SessionFactory() as session:
        await document_ai.run(session, doc_id)
    docs = (await client.get("/api/v1/medical/documents", headers=auth)).json()
    analysis = next(d for d in docs if d["id"] == doc_id)["analysis"]
    assert [(v["key"], v["origin"]) for v in analysis["values"]] == [
        ("bio.hba1c", "ia")
    ]
    assert analysis["rejected"] == 1
    ggt = await client.get(
        "/api/v1/measurements", params={"metric_key": "bio.ggt"}, headers=auth
    )
    assert ggt.status_code == 404 or ggt.json() == []


async def test_model_down_keeps_exact_values(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def down(prompt: str, model: str, **_: object) -> dict:
        raise RuntimeError("ollama unreachable")

    monkeypatch.setattr(ollama, "generate_json", down)
    lines = ["Preleve le 11-09-2026 08:00", "Plaquettes [AC] 243 G/L (150-400)"]
    doc_id = await _upload(client, auth, lines, "biologie")
    async with SessionFactory() as session:
        await document_ai.run(session, doc_id)
    docs = (await client.get("/api/v1/medical/documents", headers=auth)).json()
    analysis = next(d for d in docs if d["id"] == doc_id)["analysis"]
    assert analysis["ai_error"] == "ollama unreachable"
    assert analysis["values"][0]["key"] == "bio.plaquettes"


async def test_analyze_endpoints(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    doc_id = await _upload(client, auth, [_TEXT], "autre")
    one = await client.post(
        f"/api/v1/medical/documents/{doc_id}/analyze", headers=auth
    )
    assert one.status_code == 202
    every = await client.post(
        "/api/v1/medical/documents/analyze-all", headers=auth
    )
    assert every.status_code == 202
    assert isinstance(every.json()["queued"], int)
