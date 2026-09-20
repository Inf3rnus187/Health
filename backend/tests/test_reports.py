"""Report generation (inline fallback builds without a worker)."""

from __future__ import annotations

from httpx import AsyncClient

REPORTS = "/api/v1/reports"
MEAS = "/api/v1/measurements"


async def _seed(client: AsyncClient, auth: dict[str, str]) -> None:
    body = {
        "items": [
            {"metric_key": "body.weight", "date_key": "2026-06-01", "value": 86}
        ]
    }
    await client.post(MEAS, json=body, headers=auth)


async def test_clinical_pdf_report(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _seed(client, auth)
    created = await client.post(
        REPORTS, json={"type": "clinical_pdf"}, headers=auth
    )
    assert created.status_code == 202
    report_id = created.json()["id"]
    detail = await client.get(f"{REPORTS}/{report_id}", headers=auth)
    assert detail.json()["status"] == "ready"
    served = await client.get(f"{REPORTS}/{report_id}/file", headers=auth)
    assert served.status_code == 200
    assert served.content[:4] == b"%PDF"


async def test_caregiver_pdf_with_care_record(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """The clinical PDF builds with conditions/treatments/appointments/docs."""
    await _seed(client, auth)
    await client.post(
        "/api/v1/conditions",
        json={"name": "Asthme", "status": "active"},
        headers=auth,
    )
    await client.post(
        "/api/v1/treatments", json={"name": "Ventoline"}, headers=auth
    )
    await client.post(
        "/api/v1/appointments",
        json={"title": "Pneumologue", "starts_at": "2026-03-01T09:00:00Z"},
        headers=auth,
    )
    await client.post(
        "/api/v1/medical/documents",
        data={"kind": "biologie", "title": "NFS"},
        files={"file": ("nfs.pdf", b"%PDF-1.4 x", "application/pdf")},
        headers=auth,
    )
    created = await client.post(
        REPORTS, json={"type": "clinical_pdf"}, headers=auth
    )
    report_id = created.json()["id"]
    detail = await client.get(f"{REPORTS}/{report_id}", headers=auth)
    assert detail.json()["status"] == "ready"
    served = await client.get(f"{REPORTS}/{report_id}/file", headers=auth)
    assert served.content[:4] == b"%PDF"


async def test_csv_report(client: AsyncClient, auth: dict[str, str]) -> None:
    await _seed(client, auth)
    created = await client.post(REPORTS, json={"type": "csv"}, headers=auth)
    report_id = created.json()["id"]
    served = await client.get(f"{REPORTS}/{report_id}/file", headers=auth)
    assert served.status_code == 200
    assert "metric_key" in served.text


async def test_unknown_report_type(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(REPORTS, json={"type": "docx"}, headers=auth)
    assert response.status_code == 422
