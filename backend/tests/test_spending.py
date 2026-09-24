"""Spending on meals paid for: Uber Eats orders and other deliveries."""

from __future__ import annotations

from httpx import AsyncClient

URL = "/api/v1/spending/meals"

ORDERS = [
    ("2026-03-02T12:30", "Pizzeria Test", "18.50"),
    ("2026-03-02T22:40", "Burger Test", "24.90"),
    ("2026-03-10T23:15", "Burger Test", "21.10"),
    ("2026-04-01T13:00", "Sushi Test", "32.00"),
]


async def _order(
    client: AsyncClient, auth: dict[str, str], at: str, name: str, price: str
) -> None:
    res = await client.post(
        "/api/v1/evidence",
        data={"occurred_at": at, "kind": "livraison", "title": name,
              "amount": price},
        headers=auth,
    )  # fmt: skip
    assert res.status_code == 201, res.text


async def test_what_deliveries_cost(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for at, name, price in ORDERS:
        await _order(client, auth, at, name, price)
    await client.post(  # a taxi is not a meal
        "/api/v1/evidence",
        data={"occurred_at": "2026-03-03T08:00", "kind": "taxi",
              "amount": "40"},
        headers=auth,
    )  # fmt: skip
    span = {"start": "2026-03-01", "end": "2026-04-30"}
    body = (await client.get(URL, params=span, headers=auth)).json()
    assert (body["total"], body["count"], body["average"]) == (96.5, 4, 24.12)
    assert body["largest"]["name"] == "Sushi Test"
    assert body["late"] == {"count": 2, "total": 46.0}
    assert body["bucket"] == "day"  # 61 days
    assert len(body["periods"]) == 61
    assert body["periods"][1] == {"start": "2026-03-02", "total": 43.4,
                                  "count": 2}  # fmt: skip
    assert body["hours"][22]["count"] == 1 and body["hours"][22]["late"]
    top = body["vendors"][0]
    assert (top["name"], top["count"], top["total"]) == ("Burger Test", 2, 46.0)
    monthly = await client.get(
        URL, params={**span, "bucket": "month"}, headers=auth
    )
    months = monthly.json()["periods"]
    assert [(m["start"], m["total"]) for m in months] == [
        ("2026-03-01", 64.5),
        ("2026-04-01", 32.0),
    ]


async def test_spending_from_the_first_order(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _order(client, auth, "2025-01-15T20:00", "Pizzeria Test", "15")
    body = (
        await client.get(URL, params={"end": "2026-03-14"}, headers=auth)
    ).json()
    assert body["start"] == "2025-01-15" and body["bucket"] == "month"
    assert body["count"] == 1 and len(body["periods"]) == 15  # 01/25-03/26
    empty = await client.get(URL, params={"kind": "repas"}, headers=auth)
    assert empty.json()["count"] == 0 and empty.json()["average"] is None
    wrong = await client.get(URL, params={"kind": "taxi"}, headers=auth)
    assert wrong.status_code == 422
