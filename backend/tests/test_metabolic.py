"""Validated metabolic / liver markers (formulas, bands, API)."""

from __future__ import annotations

import pytest
from app.services import biology_catalog as bio
from app.services import metabolic_catalog as mcat
from app.services import metabolic_scores as score
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from httpx import AsyncClient


def test_formulas_match_published_definitions() -> None:
    assert score.whtr(100, 180) == pytest.approx(0.556, abs=0.001)
    assert score.bmi(90, 180) == pytest.approx(27.78, abs=0.01)
    assert score.fli(1.5, 30, 50, 100) == pytest.approx(78.7, abs=0.2)
    assert score.fib4(50, 30, 40, 250) == pytest.approx(0.949, abs=0.001)
    assert score.tyg(1.5, 1.0) == pytest.approx(8.923, abs=0.001)


_LAB = [
    "Preleve le 01-09-2026 08:00 au laboratoire",
    "Plaquettes [AC] 250 G/L (150-400)",
    "ASAT [AC] 30 U/L (< 50)",
    "ALAT [AC] 40 U/L (< 50)",
    "GGT [AC] 50 U/L (12-64)",
    "Glycemie a jeun [AC] 1,00 g/L (0,70-1,10)",
    "HBA1c - Hemoglobine glyquee (NGSP) [AC] 6,0 % (4,0-6,0)",
    "Triglycerides [AC] 1,50 g/L (< 1,50)",
]


def _lab_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in _LAB:
        pdf.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def test_marker_lab_keys_are_the_ones_the_import_writes() -> None:
    known = {bio.metric_key(a.key) for a in bio.ANALYTES}
    lab_keys = {
        key
        for keys in mcat.SOURCES.values()
        for key in keys
        if key.startswith(bio.KEY_PREFIX)
    }
    assert lab_keys
    assert lab_keys <= known


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
    imported = await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", _lab_pdf(), "application/pdf")},
        headers=auth,
    )
    assert imported.status_code == 200
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
    used = {i["label"]: i for i in markers["fib4"]["inputs"]}
    assert used["ASAT"]["value"] == 30
    assert used["Plaquettes"]["unit"] == "G/L"
    assert used["ASAT"]["date"] == "2026-09-01"
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


async def test_fibroscan_outranks_indirect_scores(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/evolution/profile",
        json={"cap_db_m": 356, "lsm_kpa": 5.2, "date_key": "2026-09-15"},
        headers=auth,
    )
    assert resp.status_code == 200
    markers = _by_key(resp.json())
    assert markers["cap"]["level"] == "high"
    assert markers["cap"]["interpretation"].startswith("S3")
    assert markers["cap"]["date"] == "2026-09-15"
    assert markers["lsm"]["level"] == "ok"
    assert "FibroScan du 15/09/2026" in markers["fli"]["note"]
    assert "FibroScan" in markers["fib4"]["note"]
    assert markers["tyg"]["note"] is None
    assert resp.json()["profile"]["cap_db_m"] == 356


_HISTORY = [
    "Preleve le 11-09-2026 08:00 au laboratoire",
    "Intervalle de reference Anteriorites",
    "15-01-2025",
    "HBA1c - Hemoglobine glyquee (NGSP) [AC] 7,9 % (4,0-6,0) 6,3",
    "Triglycerides [AC] 3,93 g/L (< 1,50) 2,10",
    "Glycemie a jeun [AC] 1,61 g/L (0,70-1,10) 1,20",
]


async def test_marker_history_uses_previous_results(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in _HISTORY:
        pdf.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", bytes(pdf.output()), "application/pdf")},
        headers=auth,
    )
    resp = await client.get("/api/v1/evolution/markers", headers=auth)
    markers = _by_key(resp.json())
    hba1c = markers["hba1c"]["history"]
    assert [(p["date"], p["value"]) for p in hba1c] == [
        ("2025-01-15", 6.3),
        ("2026-09-11", 7.9),
    ]
    assert [p["level"] for p in hba1c] == ["warn", "high"]
    tyg = markers["tyg"]["history"]
    assert [p["date"] for p in tyg] == ["2025-01-15", "2026-09-11"]
