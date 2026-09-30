"""The daily-value list: the schema's exact answer, each user their own."""

from __future__ import annotations

from app.core.db import SessionFactory
from app.models.measurement import Measurement
from app.schemas.measurement import MeasurementOut
from app.services import measurement_list
from httpx import AsyncClient
from pydantic import TypeAdapter
from sqlalchemy import select

MEAS = "/api/v1/measurements"
#: One value of each type, a bool False among them (not « nothing »).
ITEMS = [
    {"metric_key": "body.weight", "date_key": "2026-09-01", "value": 81.25},
    {"metric_key": "photo.face_done", "date_key": "2026-09-01", "value": False},
    {"metric_key": "nap.start", "date_key": "2026-09-02", "value": "13:30:00"},
    {"metric_key": "ctx.date", "date_key": "2026-09-02", "value": "Été"},
]


async def test_the_list_is_what_the_schema_writes(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    sent = await client.post(MEAS, json={"items": ITEMS}, headers=auth)
    assert sent.status_code == 201, sent.text
    listed = await client.get(MEAS, headers=auth)
    me = (await client.get("/api/v1/auth/me", headers=auth)).json()["id"]
    async with SessionFactory() as session:
        rows = await session.scalars(
            select(Measurement)
            .where(Measurement.user_id == me)
            .order_by(*measurement_list.ORDER)
        )
        schema = TypeAdapter(list[MeasurementOut])
        expected = schema.dump_json(
            schema.validate_python(list(rows), from_attributes=True)
        )
    assert listed.content == expected
    values = [row["value"] for row in listed.json()]
    assert values == [81.25, False, "13:30:00", "Été"]


async def test_each_user_lists_only_theirs(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    await client.post(MEAS, json={"items": ITEMS[:1]}, headers=auth)
    assert (await client.get(MEAS, headers=member)).json() == []
    one = (await client.get(MEAS, headers=auth)).json()
    assert [row["value"] for row in one] == [81.25]
