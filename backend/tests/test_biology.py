"""Biology import: catalog-driven parsing + purge into tracked series."""

from __future__ import annotations

from app.services import biology
from app.services import biology_catalog as cat
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from httpx import AsyncClient

_LINES = [
    "Preleve le 11-09-2026 12:02 au laboratoire",
    "Intervalle de reference Anteriorites",
    "15-01-2025",
    "Hemoglobine [AC] 15,9 g/dL (13,4-16,7) 16,7",
    "Polynucleaires neutrophiles [AC] 51,8 % 4,79 G/L (1,80-6,80) 3,86",
    "Sodium serique [AC]",
    "(Potentiometrie indirecte)",
    "138 mmol/L (136-145)",
    "27-05-2025",
    "HBA1c - Hemoglobine glyquee (NGSP) [AC]",
    "(Chromatographie liquide haute performance (HPLC))",
    "7,9 % (4,0-6,0) 6,3",
    "soit (IFCC) [AC] 63 mmol/mol (20-42) 45",
    "Cholesterol total [AC] 1,92 g/L (< 1,90) 2,10",
    "Cholesterol non-HDL 1,71 g/L (< 1,50) 1,91",
    "Triglycerides [AC] 3,93 g/L (< 1,50) 7,20",
    "Cholesterol LDL calcule si",
    "triglycerides > 3,4 g/L (soit 3,9 mmol/L).",
    "Vitamine B12 * [AC] 476,0 pg/mL (197,0-771,0) 529",
]


def _keyed() -> dict[str, list[biology.Reading]]:
    out: dict[str, list[biology.Reading]] = {}
    for reading in biology.parse_text("\n".join(_LINES)):
        out.setdefault(reading.key, []).append(reading)
    return out


def test_catalog_match_rejects_continuations() -> None:
    assert cat.match("soit (IFCC) [AC]") is None
    assert cat.match("(Potentiometrie indirecte)") is None
    assert cat.match("Creatinine [AC]").key == "creatinine"
    assert cat.match("Cholesterol non-HDL 1,71").key == "cholesterol_non_hdl"


def test_percent_then_absolute_uses_the_absolute() -> None:
    neut = _keyed()["bio.neutrophiles"]
    assert {r.value for r in neut} == {4.79, 3.86}


def test_name_on_its_own_line_is_paired_with_value() -> None:
    sodium = _keyed()["bio.sodium"]
    assert len(sodium) == 1
    assert sodium[0].value == 138.0


def test_hba1c_and_antecedent_dates() -> None:
    hba1c = _keyed()["bio.hba1c"]
    assert {r.value for r in hba1c} == {7.9, 6.3}
    assert sorted(r.day.isoformat() for r in hba1c) == [
        "2025-05-27",
        "2026-09-11",
    ]


def test_no_junk_metrics_created() -> None:
    keys = set(_keyed())
    assert not any("soit" in k for k in keys)
    total = _keyed()["bio.cholesterol_total"]
    assert {r.value for r in total} == {1.92, 2.1}
    triglycerides = {r.value for r in _keyed()["bio.triglycerides"]}
    assert 3.4 not in triglycerides
    assert "bio.vitamine_b12" in keys


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
    assert response.json()["added"] >= 8
    listed = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "bio.hba1c"},
        headers=auth,
    )
    assert len(listed.json()) == 2
    docs = (await client.get("/api/v1/medical/documents", headers=auth)).json()
    assert any(d["kind"] == "biologie" for d in docs)


async def test_biology_purge_removes_values(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", _lab_pdf(), "application/pdf")},
        headers=auth,
    )
    purged = await client.request(
        "DELETE", "/api/v1/biology/values", headers=auth
    )
    assert purged.status_code == 200
    assert purged.json()["values"] > 0
    assert purged.json()["metrics"] > 0
    listed = await client.get(
        "/api/v1/measurements",
        params={"metric_key": "bio.hba1c"},
        headers=auth,
    )
    assert listed.status_code == 404


async def test_biology_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/biology/import",
        files={"file": ("lab.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401
