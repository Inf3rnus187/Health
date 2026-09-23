"""Traces: rides, deliveries, transport, expense reports; meals with price."""

from __future__ import annotations

import io
from typing import Any

import pytest
from app.services import meal_ai
from httpx import AsyncClient
from openpyxl import Workbook

TRACES = "/api/v1/traces/import"

# Uber-like trips export (UTC times written "+0000 UTC").
_RIDES = (
    "City,Product Type,Trip or Order Status,Request Time,Begin Trip Time,"
    "Begin Trip Address,Dropoff Time,Fare Amount,Fare Currency\n"
    "Paris,UberX,COMPLETED,2026-03-02 22:31:00 +0000 UTC,"
    "2026-03-02 22:40:00 +0000 UTC,1 rue du Bureau,"
    "2026-03-02 23:05:00 +0000 UTC,31.20,EUR\n"
    "Paris,UberX,CANCELED,2026-03-03 22:00:00 +0000 UTC,,,,0,EUR\n"
    "Paris,UberX,COMPLETED,2026-03-07 21:00:00 +0000 UTC,"
    "2026-03-07 21:10:00 +0000 UTC,1 rue du Bureau,"
    "2026-03-07 21:40:00 +0000 UTC,28.00,EUR\n"
)
# Uber Eats-like export: one row per item, the order total repeated.
_EATS = (
    "Order ID;Restaurant Name;Order Time;Item Name;Order Price;Order Status\n"
    "A1;Burger Palace;02/03/2026 21:15;Double cheese;24,90 €;Completed\n"
    "A1;Burger Palace;02/03/2026 21:15;Frites;24,90 €;Completed\n"
)
_NAVIGO = "Date;Heure;Station\n02/03/2026;07:52;Châtelet\n"


def _expenses() -> bytes:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(["Note de frais mars 2026"])
    sheet.append(["Date", "Nature", "Montant TTC"])
    sheet.append(["2026-03-02", "Hôtel Ibis, nuit après astreinte", 89.5])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


async def _import(
    client: AsyncClient,
    auth: dict[str, str],
    files: list[tuple[str, bytes, str]],
    **params: Any,
) -> Any:
    res = await client.post(
        TRACES,
        files=[
            ("files", (name, data, "text/plain")) for name, data, _ in files
        ],
        data={"kinds": [kind for _, _, kind in files]},
        params={k: str(v).lower() for k, v in params.items()},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_exports_are_read_by_their_columns(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    files = [
        ("trips_data.csv", _RIDES.encode(), "taxi"),
        ("navigo.csv", _NAVIGO.encode(), "transport"),
        ("frais.xlsx", _expenses(), "frais"),
    ]
    preview = await _import(client, auth, files, dry_run=True)
    rides, metro, expenses = preview["files"]
    assert (rides["traces"], rides["skipped_count"]) == (2, 1)  # 1 cancelled
    assert rides["preview"][0]["time"] == "23:40"  # 22:40 UTC → Paris
    assert rides["preview"][0]["end"] == "00:05"
    assert rides["total"] == 59.2
    assert metro["preview"][0] == {
        "day": "2026-03-02", "time": "07:52", "end": None,
        "place": "Châtelet", "amount": None, "what": "",
    }  # fmt: skip
    assert expenses["total"] == 89.5
    done = await _import(client, auth, files)
    assert [f["stored"] for f in done["files"]] == [2, 1, 1]
    again = await _import(client, auth, files)
    assert [f["duplicates"] for f in again["files"]] == [2, 1, 1]


async def test_a_delivery_becomes_a_priced_meal_in_the_file(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    await client.post(
        "/api/v1/work/sessions",
        json={"start_at": "2026-03-02T08:00", "end_at": "2026-03-02T21:00"},
        headers=auth,
    )
    files = [
        ("eats_order_details.csv", _EATS.encode(), "livraison"),
        ("trips_data.csv", _RIDES.encode(), "taxi"),
    ]
    report = await _import(client, auth, files, meals=True)
    assert report["files"][0]["traces"] == 1  # two items, one order
    assert report["meals"] == 1
    meals = await client.get(
        "/api/v1/meals",
        params={"start": "2026-03-01", "end": "2026-03-07"},
        headers=auth,
    )
    (meal,) = meals.json()
    assert (meal["price"], meal["vendor"]) == (24.9, "Burger Palace")
    assert "Double cheese, Frites" in meal["description"]
    health = await client.get(
        "/api/v1/work/health",
        params={"start": "2026-03-01", "end": "2026-03-08"},
        headers=auth,
    )
    traces = health.json()["traces"]
    assert traces["deliveries"]["orders"] == 1
    assert traces["deliveries"]["on_long_days"] == 1
    assert traces["unclocked_days"] == ["2026-03-07"]  # a ride, no clocking
    assert {x["kind"] for x in traces["late"]} == {"livraison", "taxi"}


async def test_a_trace_typed_by_hand_with_its_meal(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    made = await client.post(
        "/api/v1/evidence",
        data={
            "occurred_at": "2026-03-04T22:10", "kind": "livraison",
            "title": "Sushi", "description": "plateau 18 pièces",
            "place": "Sushi Shop", "amount": "27,50", "meal": "true",
            "ended_at": "",  # an empty field, as a web form sends it
        },
        headers=auth,
    )  # fmt: skip
    body = made.json()
    assert body["meal_id"] and body["amount"] == 27.5
    parking = await client.post(
        "/api/v1/evidence",
        data={
            "occurred_at": "2026-03-04T07:40", "ended_at": "2026-03-04T22:30",
            "kind": "parking", "place": "Parking Indigo", "amount": "24",
        },
        headers=auth,
    )  # fmt: skip
    assert parking.json()["ended_at"].startswith("2026-03-04T21:30")
