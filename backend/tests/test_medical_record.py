"""The record (Dossier) and the condition follow-up (Suivi)."""

from __future__ import annotations

from datetime import date

from app.core.db import SessionFactory
from app.models.medical import MedicalDocument
from app.models.user import User
from app.services import biology
from app.services.biology import Reading
from app.services.condition_links import indicators_for
from httpx import AsyncClient
from sqlalchemy import select

_CAP = "liver.cap"


async def _user_id() -> str:
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalars().first()
        assert user is not None
        return user.id


def _analysis() -> dict:
    return {
        "summary": "Stéatose hépatique S3 sans fibrose.",
        "findings": ["CAP 376 dB/m"],
        "medications": [
            {
                "name": "Metformine 1000 mg",
                "dose": "1000 mg",
                "frequency": "2/j",
            },
            {"name": "Candesartan", "dose": "8 mg", "frequency": "1/j"},
        ],
        "conditions": ["Stéatose hépatique"],
        "values": [
            {
                "key": _CAP,
                "label": "CAP",
                "value": 376,
                "unit": "dB/m",
                "date": "2026-09-16",
                "origin": "lecture",
            }
        ],
    }


async def _seed() -> str:
    """One read FibroScan document and two CAP values; the document id."""
    user_id = await _user_id()
    async with SessionFactory() as session:
        doc = MedicalDocument(
            user_id=user_id,
            kind="imagerie",
            title="FibroScan",
            doc_date=date(2026, 9, 16),
            file_path="unused",
            analysis_status="done",
            analysis=_analysis(),
        )
        session.add(doc)
        readings = [
            Reading(_CAP, "CAP", "dB/m", date(2025, 3, 1), 340.0),
            Reading(_CAP, "CAP", "dB/m", date(2026, 9, 16), 376.0),
        ]
        await biology.store(session, user_id, readings, source="document")
        await session.commit()
        return doc.id


async def test_record_links_documents_results_and_suggestions(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    doc_id = await _seed()
    await client.post(
        "/api/v1/treatments", json={"name": "Candésartan"}, headers=auth
    )
    record = (await client.get("/api/v1/medical/record", headers=auth)).json()
    assert [t["name"] for t in record["suggested_treatments"]] == [
        "Metformine 1000 mg"
    ]
    cond = record["suggested_conditions"][0]
    assert cond["name"] == "Stéatose hépatique"
    assert cond["documents"][0]["id"] == doc_id
    cap = next(r for r in record["results"] if r["key"] == _CAP)
    assert cap["latest"]["value"] == 376
    assert cap["latest"]["document"]["id"] == doc_id
    assert cap["previous"]["date"] == "2025-03-01"
    assert cap["change"] == 36
    assert record["timeline"][0]["type"] == "document"
    assert record["documents"][0]["values"] == 1


async def test_declared_condition_follows_its_indicators(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    doc_id = await _seed()
    await client.post(
        "/api/v1/conditions", json={"name": "stéatose hépatique"}, headers=auth
    )
    record = (await client.get("/api/v1/medical/record", headers=auth)).json()
    assert record["suggested_conditions"] == []
    care = (await client.get("/api/v1/care/overview", headers=auth)).json()
    assert care[0]["name"] == "stéatose hépatique"
    assert [i["key"] for i in care[0]["indicators"]] == [_CAP]
    cap = care[0]["indicators"][0]
    assert cap["latest"]["value"] == 376
    # Dated by the exam, not by the import; the whole history is kept.
    assert cap["latest"]["at"].startswith("2026-09-16")
    assert [p["date"] for p in cap["series"]] == ["2025-03-01", "2026-09-16"]
    assert [d["id"] for d in care[0]["documents"]] == [doc_id]


def test_condition_names_map_to_indicators() -> None:
    assert indicators_for("MASLD (foie gras)")[:2] == [_CAP, "liver.lsm"]
    assert "bio.hba1c" in indicators_for("Diabète de type 2")
    assert "habit.cigarettes" in indicators_for("Tabagisme actif")
    assert indicators_for("Entorse de la cheville") == []
