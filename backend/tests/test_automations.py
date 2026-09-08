"""Automations: CRUD and run (reminder + capture actions)."""

from __future__ import annotations

from httpx import AsyncClient

AUTO = "/api/v1/automations"


async def _create(
    client: AsyncClient, auth: dict[str, str], action: dict
) -> str:
    response = await client.post(
        AUTO,
        json={"name": "test", "trigger": "nfc", "action": action},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_crud_and_list(client: AsyncClient, auth: dict[str, str]) -> None:
    automation_id = await _create(client, auth, {"type": "reminder"})
    listed = await client.get(AUTO, headers=auth)
    assert any(a["id"] == automation_id for a in listed.json())
    patched = await client.patch(
        f"{AUTO}/{automation_id}",
        json={"is_active": False},
        headers=auth,
    )
    assert patched.json()["is_active"] is False
    deleted = await client.delete(f"{AUTO}/{automation_id}", headers=auth)
    assert deleted.status_code == 200


async def test_invalid_trigger(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    response = await client.post(
        AUTO,
        json={"name": "x", "trigger": "telepathy", "action": {}},
        headers=auth,
    )
    assert response.status_code == 422


async def test_run_reminder(client: AsyncClient, auth: dict[str, str]) -> None:
    action = {"type": "reminder", "message": "Bois de l'eau"}
    automation_id = await _create(client, auth, action)
    response = await client.post(f"{AUTO}/{automation_id}/run", headers=auth)
    assert response.status_code == 200
    assert response.json()["message"] == "Bois de l'eau"


async def test_run_capture(client: AsyncClient, auth: dict[str, str]) -> None:
    action = {"type": "capture", "capture": {"weight": 82.0}}
    automation_id = await _create(client, auth, action)
    response = await client.post(f"{AUTO}/{automation_id}/run", headers=auth)
    assert response.status_code == 200
    assert response.json()["event_id"]
