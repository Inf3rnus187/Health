"""Doctor-delivered CDA import into the clinical observation browser."""

from __future__ import annotations

from httpx import AsyncClient

_CDA = (
    '<?xml version="1.0"?>\n'
    '<ClinicalDocument xmlns="urn:hl7-org:v3" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<component><structuredBody><component><section><entry>"
    "<observation>"
    '<code code="2339-0" displayName="Glucose" codeSystemName="LOINC"/>'
    '<effectiveTime value="20260115"/>'
    '<value xsi:type="PQ" value="5.4" unit="mmol/L"/>'
    "</observation></entry>"
    "<entry><observation>"
    '<code code="718-7" displayName="Hémoglobine"/>'
    '<effectiveTime value="20260115"/>'
    '<value xsi:type="PQ" value="14.2" unit="g/dL"/>'
    "</observation></entry>"
    "</section></component></structuredBody></component></ClinicalDocument>"
)


async def test_cda_import(client: AsyncClient, auth: dict[str, str]) -> None:
    response = await client.post(
        "/api/v1/clinical/import",
        files={"file": ("dossier.xml", _CDA.encode(), "application/xml")},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["observations"] == 2
    obs = await client.get("/api/v1/clinical/observations", headers=auth)
    body = obs.json()
    assert body["total"] == 2
    labels = {item["label"] for item in body["items"]}
    assert "Glucose" in labels


async def test_cda_import_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/clinical/import",
        files={"file": ("d.xml", b"<x/>", "application/xml")},
    )
    assert response.status_code == 401
