"""Raw exports: CSV, JSON, XLSX and FHIR."""

from __future__ import annotations

from httpx import AsyncClient

MEAS = "/api/v1/measurements"
EXPORT = "/api/v1/export"


async def _seed(client: AsyncClient, auth: dict[str, str]) -> None:
    body = {
        "items": [
            {"metric_key": "body.weight", "date_key": "2026-06-01", "value": 86}
        ]
    }
    await client.post(MEAS, json=body, headers=auth)


async def test_csv_export(client: AsyncClient, auth: dict[str, str]) -> None:
    await _seed(client, auth)
    response = await client.get(EXPORT, params={"format": "csv"}, headers=auth)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "date,metric_key,value,unit,source" in response.text


async def test_json_export(client: AsyncClient, auth: dict[str, str]) -> None:
    await _seed(client, auth)
    response = await client.get(EXPORT, params={"format": "json"}, headers=auth)
    assert response.status_code == 200
    assert response.json()[0]["metric_key"] == "body.weight"


async def test_xlsx_export(client: AsyncClient, auth: dict[str, str]) -> None:
    await _seed(client, auth)
    response = await client.get(EXPORT, params={"format": "xlsx"}, headers=auth)
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


async def test_fhir_export(client: AsyncClient, auth: dict[str, str]) -> None:
    await _seed(client, auth)
    response = await client.get(EXPORT, params={"format": "fhir"}, headers=auth)
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Observation"


async def test_invalid_format(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.get(EXPORT, params={"format": "pdf"}, headers=auth)
    assert response.status_code == 422
