"""Uber's own exports: rides (UTC times, addresses, price) and Eats."""

from __future__ import annotations

from typing import Any

import pytest
from app.services import meal_ai
from httpx import AsyncClient

TRACES = "/api/v1/traces/import"

_RIDE_COLUMNS = (
    "city_name,profile_type,currency_code,timezone,global_product_name,"
    "request_timestamp_local,request_timestamp_utc,request_lat,request_lng,"
    "begintrip_timestamp_local,begintrip_timestamp_utc,begintrip_lat,"
    "begintrip_lng,dropoff_timestamp_local,dropoff_timestamp_utc,"
    "dropoff_lat,dropoff_lng,begintrip_string,destination_string,"
    "trip_distance_miles,trip_duration_seconds,status,"
    "client_upfront_fare_local,original_fare_local,"
    "tip_amount_local_currency\n"
)
# The *_local times carry a false "Z": 12:44 local is 11:44 UTC in
# winter. City "Paris" is the account's zone, the ride is elsewhere.
_RIDES = _RIDE_COLUMNS + (
    "Paris,Personal,EUR,Europe/Paris,UberX,"
    "2026-02-04T12:31:15.000Z,2026-02-04T11:31:15.000Z,49.1,2.4,"
    "2026-02-04T12:44:28.000Z,2026-02-04T11:44:28.000Z,49.24761,2.46218,"
    "2026-02-04T12:57:37.000Z,2026-02-04T11:57:37.000Z,49.30551,2.45066,"
    '"1 rue du Test, 60100 Villetest, FR","2 allée Fictive, 60290 Autreville",'
    "7.95385,789,completed,12.19,20.19,5.0\n"
    "Paris,Business,EUR,Europe/Paris,UberX,"
    "2026-02-05T21:15:14.000Z,2026-02-05T20:15:14.000Z,48.87,2.35,"
    ",,,,,,,,Gare Fictive,"
    '"1 rue du Test, 60100 Villetest, FR",,,rider_canceled,56.65,0.0,\n'
)
_ORDERS = (
    "City_Name,Restaurant_Name,Request_Time_Local,Final_Delivery_Time_Local,"
    "Order_Status,Item_Name,Item_quantity,Customizations,"
    "Customization_Cost_Local,Special_Instructions,Item_Price,Order_Price,"
    "Currency\n"
    "Paris,Pizzeria Test - Villetest,2026-07-13T21:10:01.000Z,"
    '2026-07-13T21:47:15.000Z,completed,Pizza 4 fromages,2,"",,"",24.0,'
    "28.5,EUR\n"
    "Paris,Pizzeria Test - Villetest,2026-07-13T21:10:01.000Z,"
    '2026-07-13T21:47:15.000Z,completed,Nuggets,1,15 pièces,6.0,"",6.5,'
    "28.5,EUR\n"
    "Paris,Pizzeria Test - Villetest,2026-07-13T21:10:01.000Z,"
    '2026-07-13T21:47:15.000Z,completed,Nuggets,1,Ketchup,0.5,"",6.5,'
    "28.5,EUR\n"
    "Paris,Pizzeria Test - Villetest,2026-07-11T19:03:03.000Z,"
    '2026-07-11T19:05:40.000Z,canceled,Pizza,1,"",,"",9.5,0.0,EUR\n'
)


async def _import(
    client: AsyncClient, auth: dict[str, str], name: str, data: str, **q: Any
) -> dict[str, Any]:
    res = await client.post(
        TRACES,
        files=[("files", (name, data.encode(), "text/csv"))],
        data={"kinds": ["auto"]},
        params={k: str(v).lower() for k, v in q.items()},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    file: dict[str, Any] = res.json()["files"][0]
    return file


async def test_rides_keep_their_true_times_places_and_price(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    found = await _import(
        client, auth, "rider_lifetime_trips-0.csv", _RIDES, dry_run=True
    )
    assert (found["traces"], found["skipped_count"]) == (1, 1)
    (ride,) = found["preview"]
    assert (ride["kind"], ride["time"], ride["end"]) == (
        "taxi", "12:44", "04/02 12:57",
    )  # fmt: skip
    assert ride["place"] == "1 rue du Test, 60100 Villetest, FR"
    assert ride["title"] == (
        "Uber UberX : 1 rue du Test, 60100 Villetest, FR → "
        "2 allée Fictive, 60290 Autreville"
    )
    assert ride["amount"] == 12.19  # the price paid, after the discount
    for part in (
        "demandée 12:31, prise en charge 12:44, déposé 12:57",
        "12,8 km en 13 min",
        "avant remise 20,19 €",
        "pourboire 5,00 € en plus",
        "GPS départ 49.24761, 2.46218 → arrivée 49.30551, 2.45066",
    ):
        assert part in ride["what"]
    (left,) = found["skipped"]
    assert left["reason"].startswith(
        "course annulée par toi — demandée le 05/02/2026 21:15 : Gare Fictive"
    )
    assert "Paris" not in str(found["preview"])
    stored = await _import(client, auth, "rider_lifetime_trips-0.csv", _RIDES)
    assert stored["new"] == 1
    again = await _import(client, auth, "rider_lifetime_trips-0.csv", _RIDES)
    assert again["duplicates"] == 1


async def test_eats_orders_are_the_establishment_not_the_zone(
    client: AsyncClient,
    auth: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    found = await _import(
        client, auth, "user_orders-0.csv", _ORDERS, meals=True
    )
    assert (found["traces"], found["skipped_count"]) == (1, 1)
    (order,) = found["preview"]
    assert order["place"] == "Pizzeria Test - Villetest"
    assert (order["time"], order["end"]) == ("21:10", "13/07 21:47")
    assert order["amount"] == 28.5
    assert order["what"] == "2× Pizza 4 fromages, Nuggets (15 pièces, Ketchup)"
    assert found["skipped"][0]["reason"] == (
        "commande annulée — Pizzeria Test - Villetest"
    )
    meals = await client.get(
        "/api/v1/meals",
        params={"start": "2026-07-13", "end": "2026-07-13"},
        headers=auth,
    )
    (meal,) = meals.json()
    assert meal["eaten_at"].startswith("2026-07-13T19:47")  # delivered, UTC
    assert meal["price"] == 28.5
