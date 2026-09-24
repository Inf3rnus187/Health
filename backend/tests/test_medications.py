"""Medication intakes: each dose, how it came in, and the adherence."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from httpx import AsyncClient

TREATMENTS = "/api/v1/treatments"
TAKE = "/api/v1/medications/take"
PARIS = ZoneInfo("Europe/Paris")


async def _treatment(
    client: AsyncClient, auth: dict[str, str], **extra: object
) -> dict[str, object]:
    body = {"name": "Paroxétine", "dose": "20 mg", "doses_per_day": 2}
    made = await client.post(TREATMENTS, json={**body, **extra}, headers=auth)
    assert made.status_code == 201, made.text
    return dict(made.json())


async def _token(client: AsyncClient, auth: dict[str, str], scope: str) -> str:
    made = await client.post(
        "/api/v1/tokens", json={"name": scope, "scopes": [scope]}, headers=auth
    )
    return str(made.json()["token"])


async def test_each_dose_keeps_when_and_how_it_came_in(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    treatment = await _treatment(client, auth)
    url = f"{TREATMENTS}/{treatment['id']}/intakes"
    web = await client.post(url, json={}, headers=auth)
    assert web.status_code == 201, web.text
    assert (web.json()["source"], web.json()["dose"]) == ("web", "20 mg")
    shortcut = await _token(client, auth, "write:measurements")
    by_name = await client.post(
        f"{TAKE}?token={shortcut}", json={"treatment": "parox"}
    )
    assert by_name.status_code == 201, by_name.text
    assert by_name.json()["source"] == "raccourci"
    assert by_name.json()["treatment_id"] == treatment["id"]
    mcp = await _token(client, auth, "hub:full")
    skipped = await client.post(
        TAKE,
        json={"treatment": "PAROXETINE", "status": "skipped", "note": "oubli"},
        headers={"Authorization": f"Bearer {mcp}"},
    )
    assert (skipped.json()["source"], skipped.json()["status"]) == (
        "mcp",
        "skipped",
    )
    listed = await client.get("/api/v1/medications/intakes", headers=auth)
    assert [i["source"] for i in listed.json()] == ["mcp", "raccourci", "web"]
    assert all(i["created_at"] for i in listed.json())
    later = (datetime.now(PARIS) + timedelta(hours=2)).isoformat()
    future = await client.post(url, json={"taken_at": later}, headers=auth)
    assert future.status_code == 422
    unknown = await client.post(TAKE, json={"treatment": "x"}, headers=auth)
    assert unknown.status_code == 404
    read = await client.get(
        "/api/v1/medications/intakes",
        headers={"Authorization": f"Bearer {shortcut}"},
    )
    assert read.status_code == 403  # a Shortcut writes, never reads


async def test_another_user_cannot_log_or_see_my_doses(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    treatment = await _treatment(client, auth)
    url = f"{TREATMENTS}/{treatment['id']}/intakes"
    assert (await client.post(url, json={}, headers=member)).status_code == 404
    other = await client.post(
        TAKE, json={"treatment": "Paroxétine"}, headers=member
    )
    assert other.status_code == 404
    mine = await client.post(url, json={}, headers=auth)
    gone = await client.delete(
        f"/api/v1/medications/intakes/{mine.json()['id']}", headers=member
    )
    assert gone.status_code == 404
    seen = await client.get("/api/v1/medications/intakes", headers=member)
    assert seen.json() == []


def _at(day: date, hour: int) -> str:
    return datetime(
        day.year, day.month, day.day, hour, tzinfo=PARIS
    ).isoformat()


async def test_adherence_counts_planned_taken_and_gaps(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    today = datetime.now(PARIS).date()
    d = [today - timedelta(days=n) for n in (4, 3, 2, 1)]
    treatment = await _treatment(
        client,
        auth,
        start_date=d[0].isoformat(),
        end_date=d[3].isoformat(),
    )
    url = f"{TREATMENTS}/{treatment['id']}/intakes"
    doses = [
        (d[0], 8, "taken"), (d[0], 20, "taken"),
        (d[1], 8, "taken"), (d[1], 20, "skipped"),
        (d[3], 8, "taken"), (d[3], 20, "taken"),
    ]  # fmt: skip
    for day, hour, state in doses:
        body = {"taken_at": _at(day, hour), "status": state}
        res = await client.post(url, json=body, headers=auth)
        assert res.status_code == 201, res.text
    res = await client.get(
        "/api/v1/medications/adherence",
        params={"start": d[0].isoformat(), "end": today.isoformat()},
        headers=auth,
    )
    (item,) = res.json()["items"]
    assert (item["days"], item["planned"], item["taken"]) == (4, 8, 5)
    assert (item["skipped"], item["rate"], item["days_complete"]) == (
        1,
        62.5,
        2,
    )
    assert item["days_without_record"] == 1 and item["longest_gap_days"] == 1
    assert item["usual_time"] == "08:00"
    assert item["entered_late"] == 6  # all typed now, days later
    assert sum(w["taken"] for w in item["weeks"]) == 5


async def test_todays_doses(client: AsyncClient, auth: dict[str, str]) -> None:
    await _treatment(client, auth)
    await _treatment(client, auth, name="Ancien", active=False)
    await client.post(TAKE, json={"treatment": "Paroxétine"}, headers=auth)
    res = await client.get("/api/v1/medications/today", headers=auth)
    (only,) = res.json()
    assert (only["name"], only["taken"], only["doses_per_day"]) == (
        "Paroxétine",
        1,
        2,
    )
    assert only["last_id"]
