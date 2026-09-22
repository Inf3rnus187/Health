"""Tools: the medical record — documents, conditions, treatments, visits."""

from __future__ import annotations

import base64
from typing import Any

from phoenix_mcp import client
from phoenix_mcp.app import mcp


@mcp.tool()
async def medical_record() -> Any:
    """The Dossier, built from the documents.

    Documents with their AI reading; conditions and medications read in
    documents but not declared yet (to confirm); every lab / FibroScan
    result with its previous value and source document; the chronology.
    """
    return await client.get("/medical/record")


@mcp.tool()
async def care_overview() -> Any:
    """Suivi: each declared condition and its indicators.

    Latest value, change and series of each indicator, and the
    documents mentioning the condition.
    """
    return await client.get("/care/overview")


@mcp.tool()
async def list_documents() -> Any:
    """Medical documents with their AI analysis (values, summary, status)."""
    return await client.get("/medical/documents")


@mcp.tool()
async def document_text(doc_id: str) -> Any:
    """The text the AI reads from a document.

    OCR for scans. Use it to check an extraction against the source.
    """
    return await client.get(f"/medical/documents/{doc_id}/text")


@mcp.tool()
async def analyze_document(doc_id: str) -> Any:
    """(Re-)read one document with the medical models (worker, minutes)."""
    return await client.post(f"/medical/documents/{doc_id}/analyze")


@mcp.tool()
async def analyze_all_documents() -> Any:
    """(Re-)read every document with the medical models."""
    return await client.post("/medical/documents/analyze-all")


@mcp.tool()
async def upload_document(
    filename: str,
    content_base64: str,
    kind: str = "autre",
    title: str = "",
    doc_date: str = "",
    media_type: str = "application/pdf",
) -> Any:
    """Add a medical document, then call analyze_document.

    kind: ordonnance, imagerie, compte_rendu, biologie, efr,
    test_marche, vaccination or autre. ``content_base64``: the file.
    """
    data = base64.b64decode(content_base64)
    return await client.upload(
        "/medical/documents",
        {"file": (filename, data, media_type)},
        {"kind": kind, "title": title, "doc_date": doc_date},
    )


@mcp.tool()
async def delete_document(doc_id: str) -> Any:
    """Delete a medical document (its extracted values stay recorded)."""
    return await client.request("DELETE", f"/medical/documents/{doc_id}")


@mcp.tool()
async def list_conditions() -> Any:
    """Declared conditions (maladies) with status and onset."""
    return await client.get("/conditions")


@mcp.tool()
async def save_condition(
    name: str,
    status: str = "active",
    code: str | None = None,
    onset_date: str | None = None,
    notes: str | None = None,
    condition_id: str | None = None,
) -> Any:
    """Add a condition, or replace one by ``condition_id``.

    status: active, resolved or suspected; code: ICD-10 (optional).
    """
    body = {
        "name": name,
        "status": status,
        "code": code,
        "onset_date": onset_date,
        "notes": notes,
    }
    if condition_id:
        return await client.request(
            "PUT", f"/conditions/{condition_id}", body=body
        )
    return await client.post("/conditions", body)


@mcp.tool()
async def delete_condition(condition_id: str) -> Any:
    """Delete a declared condition."""
    return await client.request("DELETE", f"/conditions/{condition_id}")


@mcp.tool()
async def list_treatments() -> Any:
    """Treatments (current and stopped) with dose, frequency and dates."""
    return await client.get("/treatments")


@mcp.tool()
async def save_treatment(
    name: str,
    dose: str | None = None,
    frequency: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    active: bool = True,
    notes: str | None = None,
    treatment_id: str | None = None,
) -> Any:
    """Add a treatment, or replace one when ``treatment_id`` is given."""
    body = {
        "name": name,
        "dose": dose,
        "frequency": frequency,
        "start_date": start_date,
        "end_date": end_date,
        "active": active,
        "notes": notes,
    }
    if treatment_id:
        return await client.request(
            "PUT", f"/treatments/{treatment_id}", body=body
        )
    return await client.post("/treatments", body)


@mcp.tool()
async def delete_treatment(treatment_id: str) -> Any:
    """Delete a treatment."""
    return await client.request("DELETE", f"/treatments/{treatment_id}")


@mcp.tool()
async def list_appointments() -> Any:
    """Medical appointments (manual and imported from .ics)."""
    return await client.get("/appointments")


@mcp.tool()
async def add_appointment(
    title: str,
    starts_at: str,
    practitioner: str | None = None,
    location: str | None = None,
    notes: str | None = None,
) -> Any:
    """Add an appointment (``starts_at`` ISO datetime with offset)."""
    body = {
        "title": title,
        "starts_at": starts_at,
        "practitioner": practitioner,
        "location": location,
        "notes": notes,
    }
    return await client.post("/appointments", body)


@mcp.tool()
async def delete_appointment(appointment_id: str) -> Any:
    """Delete an appointment."""
    return await client.request("DELETE", f"/appointments/{appointment_id}")


@mcp.tool()
async def clinical_observations(
    search: str | None = None, limit: int = 50, offset: int = 0
) -> Any:
    """Observations of the imported CDA record (Mon espace santé)."""
    params = {"search": search, "limit": limit, "offset": offset}
    return await client.get("/clinical/observations", params)
