"""Delete many items at once: proofs and traces, sessions, absences, meals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.core.db import SessionFactory
from app.models.work import Evidence
from app.services import meal_ai
from httpx import AsyncClient

API = "/api/v1"
_UNKNOWN = "00000000-0000-0000-0000-000000000000"


async def _evidence(
    client: AsyncClient, auth: dict[str, str], **fields: str
) -> dict[str, Any]:
    made = await client.post(
        f"{API}/evidence",
        data=fields,
        files={"file": ("taxi.pdf", b"%PDF-1.4 fake", "application/pdf")}
        if fields.get("kind") == "taxi"
        else None,
        headers=auth,
    )
    assert made.status_code == 201, made.text
    body: dict[str, Any] = made.json()
    return body


async def test_traces_go_with_their_files_and_meals(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    ride = await _evidence(
        client, auth, occurred_at="2026-03-04T22:10", kind="taxi", place="X"
    )
    meal = await _evidence(
        client, auth, occurred_at="2026-03-04T21:00", kind="livraison",
        place="Pizzeria Test", amount="20", meal="true",
    )  # fmt: skip
    kept = await _evidence(
        client, auth, occurred_at="2026-03-04T08:00", kind="appel"
    )
    async with SessionFactory() as session:
        row = await session.get(Evidence, ride["id"])
    assert row is not None and row.file_path
    stored = Path(row.file_path)
    assert stored.exists()
    res = await client.post(
        f"{API}/evidence/delete",
        json={"ids": [ride["id"], meal["id"], _UNKNOWN], "meals": True},
        headers=auth,
    )
    assert res.json() == {"deleted": 2, "meals": 1}
    assert not stored.exists()
    left = await client.get(f"{API}/evidence", headers=auth)
    assert [x["id"] for x in left.json()] == [kept["id"]]
    gone = await client.get(f"{API}/meals/{meal['meal_id']}", headers=auth)
    assert gone.status_code == 404
    empty = await client.post(
        f"{API}/evidence/delete", json={"ids": []}, headers=auth
    )
    assert empty.status_code == 422


async def test_meals_stay_unless_asked_and_go_on_their_own(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    order = await _evidence(
        client, auth, occurred_at="2026-03-04T21:00", kind="livraison",
        place="Pizzeria Test", amount="20", meal="true",
    )  # fmt: skip
    res = await client.post(
        f"{API}/evidence/delete", json={"ids": [order["id"]]}, headers=auth
    )
    assert res.json() == {"deleted": 1, "meals": 0}
    meals = await client.post(
        f"{API}/meals/delete",
        json={"ids": [order["meal_id"], _UNKNOWN]},
        headers=auth,
    )
    assert meals.json() == {"deleted": 1, "meals": 0}


async def test_sessions_go_and_their_days_are_rebuilt(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    ids = []
    for day in ("2026-03-02", "2026-03-03"):
        made = await client.post(
            f"{API}/work/sessions",
            json={"start_at": f"{day}T08:00", "end_at": f"{day}T18:00"},
            headers=auth,
        )
        ids.append(made.json()["id"])
    res = await client.post(
        f"{API}/work/sessions/delete", json={"ids": ids}, headers=auth
    )
    assert res.json() == {"deleted": 2, "meals": 0}
    days = await client.get(
        f"{API}/work/days",
        params={"start": "2026-03-02", "end": "2026-03-03"},
        headers=auth,
    )
    assert [d["hours"] for d in days.json()] == [None, None]
    stats = await client.get(
        f"{API}/work/stats",
        params={"start": "2026-03-02", "end": "2026-03-03"},
        headers=auth,
    )
    assert stats.json()["total_hours"] == 0


async def test_absences_go_at_once(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    ids = []
    for start in ("2026-03-02", "2026-03-09"):
        made = await client.post(
            f"{API}/absences",
            json={"kind": "conge", "start_date": start, "end_date": start},
            headers=auth,
        )
        ids.append(made.json()["id"])
    res = await client.post(
        f"{API}/absences/delete", json={"ids": ids}, headers=auth
    )
    assert res.json()["deleted"] == 2
    assert (await client.get(f"{API}/absences", headers=auth)).json() == []
