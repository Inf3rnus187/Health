"""Medical documents: upload, list, view, delete, kind normalisation."""

from __future__ import annotations

from httpx import AsyncClient

MED = "/api/v1/medical/documents"
_PDF = b"%PDF-1.4 fake ordonnance bytes"


async def _upload(
    client: AsyncClient, auth: dict[str, str], kind: str = "ordonnance"
) -> dict[str, str]:
    response = await client.post(
        MED,
        data={"kind": kind, "title": "Amoxicilline", "doc_date": "2026-08-01"},
        files={"file": ("ord.pdf", _PDF, "application/pdf")},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()


async def test_upload_and_list(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await _upload(client, auth)
    assert created["kind"] == "ordonnance"
    assert created["title"] == "Amoxicilline"
    assert created["doc_date"] == "2026-08-01"
    assert created["size_bytes"] == len(_PDF)
    listed = (await client.get(MED, headers=auth)).json()
    assert any(d["id"] == created["id"] for d in listed)


async def test_download_returns_bytes(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await _upload(client, auth)
    got = await client.get(f"{MED}/{created['id']}/file", headers=auth)
    assert got.status_code == 200
    assert got.content == _PDF
    assert got.headers["content-type"].startswith("application/pdf")


async def test_unknown_kind_becomes_autre(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await _upload(client, auth, kind="n_importe_quoi")
    assert created["kind"] == "autre"


async def test_delete(client: AsyncClient, auth: dict[str, str]) -> None:
    created = await _upload(client, auth)
    removed = await client.delete(f"{MED}/{created['id']}", headers=auth)
    assert removed.status_code == 200
    listed = (await client.get(MED, headers=auth)).json()
    assert all(d["id"] != created["id"] for d in listed)


async def test_requires_auth(client: AsyncClient) -> None:
    response = await client.get(MED)
    assert response.status_code == 401
