"""The daily journal: one line per day (night, counters, meals), paged."""

from __future__ import annotations

from typing import Any

import pytest
from app.services import meal_ai
from httpx import AsyncClient

DAYS = "/api/v1/journal/days"
TALLY = "/api/v1/sync/tally"


async def _tap(
    client: AsyncClient, auth: dict[str, str], metric: str, times: int
) -> None:
    for _ in range(times):
        body = {"metric": metric, "date_key": "2026-03-04"}
        res = await client.post(TALLY, json=body, headers=auth)
        assert res.status_code == 200, res.text


async def test_a_day_of_the_journal(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_worker(*_: Any) -> bool:
        return False

    monkeypatch.setattr(meal_ai, "enqueue", no_worker)
    await _tap(client, auth, "water.bottles_1_5", 2)
    await _tap(client, auth, "habit.coffee", 3)
    await _tap(client, auth, "habit.cigarettes", 1)
    for at in ("2026-03-04T08:10:00+01:00", "2026-03-04T14:30:00+01:00"):
        pee = {"at": at}
        await client.post("/api/v1/journal/urination", json=pee, headers=auth)
    await client.post(
        "/api/v1/sleep/nights",
        json={"bedtime": "2026-03-03T23:00", "wake_time": "2026-03-04T05:00",
              "awakenings": 3},
        headers=auth,
    )  # fmt: skip
    await client.post(
        "/api/v1/meals",
        data={"meal_type": "lunch", "eaten_at": "2026-03-04T12:30",
              "description": "salade"},
        headers=auth,
    )  # fmt: skip
    res = await client.get(
        DAYS, params={"start": "2026-03-03", "end": "2026-03-04"}, headers=auth
    )
    body = res.json()
    assert body["total"] == 2
    day, before = body["items"]
    assert day["date"] == "2026-03-04" and before["date"] == "2026-03-03"
    assert (day["water_bottles"], day["water_l"]) == (2.0, 3.0)
    assert (day["coffee"], day["cigarettes"], day["pee"]) == (3.0, 1.0, 2.0)
    assert day["sleep"]["asleep_min"] == 360
    assert day["sleep"]["awakenings"] == 3
    assert (day["meals"], day["meal_kcal"]) == (1, None)
    assert before["sleep"] is None and before["coffee"] is None
    since = await client.get(DAYS, params={"end": "2026-03-05"}, headers=auth)
    # From the first day recorded: the night woken up from on 04/03.
    assert since.json()["total"] == 2


async def test_journal_pages_read_only_their_days(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    span = {"start": "2026-01-01", "end": "2026-01-31"}
    first = await client.get(DAYS, params={**span, "limit": 10}, headers=auth)
    assert first.json()["total"] == 31
    assert [d["date"] for d in first.json()["items"]][:2] == [
        "2026-01-31",
        "2026-01-30",
    ]
    last = await client.get(
        DAYS, params={**span, "limit": 10, "offset": 30}, headers=auth
    )
    assert [d["date"] for d in last.json()["items"]] == ["2026-01-01"]
    past = await client.get(DAYS, params={**span, "offset": 40}, headers=auth)
    assert past.json() == {"items": [], "total": 31}
    wrong = await client.get(
        DAYS, params={"start": "2026-02-01", "end": "2026-01-01"}, headers=auth
    )
    assert wrong.status_code == 422
