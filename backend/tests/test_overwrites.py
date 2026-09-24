"""A daily write that replaces a value keeps the old one in the audit."""

from __future__ import annotations

from app.core.db import SessionFactory
from app.models.audit import AuditLog
from httpx import AsyncClient
from sqlalchemy import select

MEASURES = "/api/v1/measurements"


async def _write(client: AsyncClient, auth: dict[str, str], value: int) -> None:
    item = {"metric_key": "habit.cigarettes", "date_key": "2026-09-20"}
    response = await client.post(
        MEASURES, json={"items": [{**item, "value": value}]}, headers=auth
    )
    assert response.status_code == 201


async def _payloads() -> list[dict[str, object]]:
    async with SessionFactory() as session:
        rows = await session.execute(
            select(AuditLog)
            .where(AuditLog.entity == "measurement")
            .order_by(AuditLog.created_at)
        )
        return [row.payload or {} for row in rows.scalars()]


async def test_replaced_value_is_kept(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _write(client, auth, 9)
    await _write(client, auth, 1)
    first, second = await _payloads()
    assert first["replaced"] == []
    assert second["replaced"] == [
        {"metric": "habit.cigarettes", "date": "2026-09-20", "previous": 9.0}
    ]


async def test_tally_steps_are_audited(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    body = {"metric": "habit.coffee", "date_key": "2026-09-20", "amount": 2}
    await client.post("/api/v1/sync/tally", json=body, headers=auth)
    (payload,) = await _payloads()
    assert payload == {
        "metric": "habit.coffee",
        "date": "2026-09-20",
        "previous": 0.0,
        "total": 2.0,
        "token_id": None,  # the web page (a Shortcut: its token's id)
    }
