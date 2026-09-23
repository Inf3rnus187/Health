"""Receipts (PDF) and expense reports: one trace, never two."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from fpdf import FPDF
from httpx import AsyncClient
from openpyxl import Workbook

TRACES = "/api/v1/traces/import"
# Ride receipts are named after the ride: "DD-MM-YYYY-HHhMM-<id>.pdf".
RECEIPT = "12-03-2026-02H15-0a1b2c3d.pdf"


def _invoice() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for text in (
        "Facture fiscale",
        "Facture emise par Uber B.V. pour:",
        "TRANSPORTS TEST",
        "Numero de facture: TEST-0001",
        "Date de facturation: 12 mars 2026",
        "Description",
        "Prix du service de transport",
        "41,36 EUR",
        "Total HT",
        "41,36 EUR",
        "Montant total a payer",
        "45,50 EUR",
    ):
        pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _expenses() -> bytes:
    """Like a real expense report: some columns have no title."""
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["Date", None, None, "Société facturante", "Montant TTC (€)",
                  "lieu de prise en c", None])  # fmt: skip
    sheet.append([datetime(2026, 3, 12), "taxi", "Uber", "TRANSPORTS TEST",
                  45.5, "Site", "Heures supp"])  # fmt: skip
    sheet.append([datetime(2026, 3, 12), "parking", None, None, 30,
                  "parking du 10/03/26 08h00 au 12/03/2026 21h30",
                  "Plusieurs jours sur site"])  # fmt: skip
    sheet.append([datetime(2026, 3, 11), "diner", None, "Le Bistrot", 22.4,
                  None, "Plusieurs jours sur site"])  # fmt: skip
    sheet.append([None, None, None, None, 97.9, None, None])  # the total
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


async def _import(
    client: AsyncClient, auth: dict[str, str], name: str, data: bytes
) -> Any:
    res = await client.post(
        TRACES,
        files=[("files", (name, data, "application/octet-stream"))],
        data={"kinds": ["auto"]},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()["files"][0]


async def _evidence(client: AsyncClient, auth: dict[str, str]) -> Any:
    return (await client.get("/api/v1/evidence", headers=auth)).json()


async def test_the_receipt_completes_the_expense_line(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    sheet = await _import(client, auth, "note_de_frais.xlsx", _expenses())
    assert (sheet["traces"], sheet["new"], sheet["skipped_count"]) == (3, 3, 1)
    receipt = await _import(client, auth, RECEIPT, _invoice())
    assert (receipt["merged"], receipt["new"]) == (1, 0)
    items = {e["kind"]: e for e in await _evidence(client, auth)}
    assert set(items) == {"taxi", "parking", "repas"}  # kinds per line
    ride = items["taxi"]
    assert ride["time_known"] and ride["occurred_at"].startswith(
        "2026-03-12T01:15"  # 02:15 Paris, from the receipt's name
    )
    assert ride["file_name"] == RECEIPT and len(ride["sha256"]) == 64
    assert "Heures supp" in ride["description"]
    assert "TEST-0001" in ride["description"]
    parking = items["parking"]
    assert parking["occurred_at"].startswith("2026-03-10T07:00")
    assert parking["ended_at"].startswith("2026-03-12T20:30")
    again = await _import(client, auth, RECEIPT, _invoice())
    assert again["duplicates"] == 1


async def test_the_expense_line_after_its_receipt_is_not_doubled(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    receipt = await _import(client, auth, RECEIPT, _invoice())
    assert receipt["new"] == 1 and receipt["preview"][0]["amount"] == 45.5
    sheet = await _import(client, auth, "note_de_frais.xlsx", _expenses())
    assert (sheet["new"], sheet["duplicates"]) == (2, 1)
    health = await client.get(
        "/api/v1/work/health",
        params={"start": "2026-03-09", "end": "2026-03-13"},
        headers=auth,
    )
    traces = health.json()["traces"]
    # The parking stay places you on site each day, never clocked.
    assert traces["unclocked_days"] == [
        "2026-03-10",
        "2026-03-11",
        "2026-03-12",
    ]
    assert {k["kind"]: k["total"] for k in traces["by_kind"]}["parking"] == 30


async def test_an_unreadable_file_is_reported_not_a_crash(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    junk = await _import(client, auth, "export.csv", b"\x00\x01garbage\x00")
    assert junk["traces"] == 0 and junk["skipped_count"] == 1
