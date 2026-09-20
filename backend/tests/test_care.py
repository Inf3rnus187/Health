"""Conditions, treatments, appointments CRUD and .ics import."""

from __future__ import annotations

from httpx import AsyncClient

BASE = "/api/v1"

_ICS = (
    "BEGIN:VCALENDAR\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-1@apple\r\n"
    "SUMMARY:Cardiologue\r\n"
    "DTSTART:20260115T090000Z\r\n"
    "DTEND:20260115T093000Z\r\n"
    "LOCATION:CHU\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


async def test_condition_crud(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        f"{BASE}/conditions",
        json={"name": "Asthme", "status": "active", "code": "J45"},
        headers=auth,
    )
    assert created.status_code == 201
    cid = created.json()["id"]
    updated = await client.put(
        f"{BASE}/conditions/{cid}",
        json={"name": "Asthme", "status": "resolved"},
        headers=auth,
    )
    assert updated.json()["status"] == "resolved"
    listed = (await client.get(f"{BASE}/conditions", headers=auth)).json()
    assert any(c["id"] == cid for c in listed)
    gone = await client.delete(f"{BASE}/conditions/{cid}", headers=auth)
    assert gone.status_code == 200


async def test_treatment_toggle_active(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    created = await client.post(
        f"{BASE}/treatments",
        json={"name": "Ventoline", "dose": "100 ug", "frequency": "2/j"},
        headers=auth,
    )
    tid = created.json()["id"]
    assert created.json()["active"] is True
    off = await client.put(
        f"{BASE}/treatments/{tid}",
        json={"name": "Ventoline", "active": False},
        headers=auth,
    )
    assert off.json()["active"] is False


async def test_appointment_manual_and_ics(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    manual = await client.post(
        f"{BASE}/appointments",
        json={"title": "Kine", "starts_at": "2026-02-01T10:00:00Z"},
        headers=auth,
    )
    assert manual.status_code == 201
    assert manual.json()["source"] == "manual"
    first = await client.post(
        f"{BASE}/appointments/import",
        files={"file": ("cal.ics", _ICS.encode(), "text/calendar")},
        headers=auth,
    )
    assert first.json()["added"] == 1
    again = await client.post(
        f"{BASE}/appointments/import",
        files={"file": ("cal.ics", _ICS.encode(), "text/calendar")},
        headers=auth,
    )
    assert again.json()["added"] == 0  # deduped by UID
    listed = (await client.get(f"{BASE}/appointments", headers=auth)).json()
    assert any(a["title"] == "Cardiologue" for a in listed)


async def test_care_requires_auth(client: AsyncClient) -> None:
    assert (await client.get(f"{BASE}/conditions")).status_code == 401
    assert (await client.get(f"{BASE}/treatments")).status_code == 401
    assert (await client.get(f"{BASE}/appointments")).status_code == 401
