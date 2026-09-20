"""Biology import: parse lab text + PDF into tracked measurements."""

from __future__ import annotations

from app.services import biology
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from httpx import AsyncClient

_LINES = [
    "Preleve le 11-09-2026 12:02 au laboratoire",
    "15-01-2025",
    "Hemoglobine [AC] 15,9 g/dL (13,4-16,7) 16,7",
    "Glycemie a jeun 1,61 g/L (0,74-1,06) 1,50",
]


def test_parse_text_keeps_antecedents() -> None:
    readings = biology.parse_text("\n".join(_LINES))
    hb = [r for r in readings if r.key == "bio.hemoglobine"]
    assert len(hb) == 2
    assert sorted(r.day.isoformat() for r in hb) == [
        "2025-01-15",
        "2026-09-11",
    ]
    assert {r.value for r in hb} == {15.9, 16.7}


def _lab_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in _LINES:
        pdf.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


async def test_biology_import_endpoint(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", _lab_pdf(), "application/pdf")},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["added"] >= 2
    listed = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "bio.hemoglobine"},
        headers=auth,
    )
    assert len(listed.json()) == 2
    docs = (await client.get("/api/v1/medical/documents", headers=auth)).json()
    assert any(d["kind"] == "biologie" for d in docs)


async def test_biology_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401
