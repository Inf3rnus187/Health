"""The iPhone app's HealthKit sync: by UUID, sums, nights, workouts."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

URL = "/api/v1/sync/healthkit"
Q = "HKQuantityTypeIdentifier"
C = "HKCategoryTypeIdentifier"
DAY = "2026-09-26"
WATCH = "Apple Watch de Test"


async def _app(client: AsyncClient, auth: dict[str, str]) -> dict[str, str]:
    made = await client.post(
        "/api/v1/tokens",
        json={"name": "App iPhone", "scopes": ["write:measurements"]},
        headers=auth,
    )
    return {"Authorization": f"Bearer {made.json()['token']}"}


async def _day(
    client: AsyncClient, auth: dict[str, str], key: str
) -> float | None:
    view = (
        await client.get(f"/api/v1/metrics/{key}/overview", headers=auth)
    ).json()
    if view.get("latest") is None:
        return None
    return view["day"]["value"] if view["day"]["date"] == DAY else None


def _hr(uuid: str, clock: str, bpm: float) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "type": f"{Q}HeartRate",
        "start": f"{DAY}T{clock}:00+02:00",
        "end": f"{DAY}T{clock}:00+02:00",
        "value": bpm,
        "unit": "count/min",
        "device": WATCH,
    }


async def test_a_sample_is_kept_by_its_uuid_and_deleted_by_it(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    app = await _app(client, auth)
    first = [_hr("A1", "08:00", 60), _hr("A2", "10:00", 80)]
    sent = await client.post(URL, json={"samples": first}, headers=app)
    assert sent.status_code == 200, sent.text
    assert sent.json()["samples"] == 2 and sent.json()["skipped"] == []
    assert await _day(client, auth, "heart.rate") == 70
    # the same UUID sent again replaces itself
    again = {"samples": [_hr("A2", "10:00", 90)]}
    await client.post(URL, json=again, headers=app)
    assert await _day(client, auth, "heart.rate") == 75
    state = (await client.get(URL, headers=app)).json()
    assert state["samples"] == 2 and state["last_sync_at"]
    assert state["metrics"][0]["key"] == "heart.rate"
    gone = await client.post(URL, json={"deleted": ["A1", "A2"]}, headers=app)
    assert gone.json()["deleted"] == 2
    assert await _day(client, auth, "heart.rate") is None  # day cleared


async def test_categories_become_numbers_and_bad_lines_are_counted(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    app = await _app(client, auth)
    lines = [
        {"uuid": "H1", "type": f"{C}Headache", "start": f"{DAY}T09:00:00",
         "end": f"{DAY}T10:00:00", "value": "HKCategoryValueSeverityModerate"},
        {"uuid": "M1", "type": f"{C}MindfulSession",
         "start": f"{DAY}T07:00:00", "end": f"{DAY}T07:10:00"},
        {"uuid": "S1", "type": f"{Q}StepCount", "start": f"{DAY}T09:00:00",
         "value": 120, "unit": "count"},
        {"uuid": "X1", "type": "Pouls", "start": f"{DAY}T09:00:00", "value": 1},
        {"uuid": "Z1", "type": f"{C}SleepAnalysis",
         "start": f"{DAY}T01:00:00", "end": f"{DAY}T02:00:00", "value": 7},
    ]  # fmt: skip
    sent = (await client.post(URL, json={"samples": lines}, headers=app)).json()
    assert sent["samples"] == 2
    reasons = {s["type"]: s["reason"] for s in sent["skipped"]}
    assert reasons[f"{Q}StepCount"].startswith("cumulé")
    assert reasons["Pouls"].startswith("type inconnu")
    assert reasons[f"{C}SleepAnalysis"].startswith("sommeil")
    assert await _day(client, auth, "apple.headache") == 2  # moderate
    assert await _day(client, auth, "apple.mindful_session") == 10  # minutes


def _steps(start: str, end: str, total: float) -> dict[str, Any]:
    return {
        "type": f"{Q}StepCount",
        "start": f"{DAY}T{start}:00+02:00",
        "end": f"{DAY}T{end}:00+02:00" if end != "24:00" else
        "2026-09-27T00:00:00+02:00",
        "sum": total,
        "unit": "count",
    }  # fmt: skip


async def test_cumulative_types_come_as_sums_never_added_twice(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    app = await _app(client, auth)
    hours = [_steps("08:00", "09:00", 400), _steps("09:00", "10:00", 600)]
    sent = await client.post(URL, json={"statistics": hours}, headers=app)
    assert sent.json()["statistics"] == 2
    assert await _day(client, auth, "activity.steps") == 1000
    later = {"statistics": [_steps("09:00", "10:00", 700)]}  # hour grew
    await client.post(URL, json=later, headers=app)
    assert await _day(client, auth, "activity.steps") == 1100
    whole = {"statistics": [_steps("00:00", "24:00", 1500)]}  # by day now
    await client.post(URL, json=whole, headers=app)
    assert await _day(client, auth, "activity.steps") == 1500
    hr = {**_steps("08:00", "09:00", 70), "type": f"{Q}HeartRate"}
    refused = await client.post(URL, json={"statistics": [hr]}, headers=app)
    assert refused.json()["skipped"][0]["reason"].startswith("ponctuel")


def _sleep(
    uuid: str, start: str, end: str, value: int, device: str
) -> dict[str, Any]:
    first = "2026-09-25" if start >= "12:00" else DAY
    return {
        "uuid": uuid,
        "type": f"{C}SleepAnalysis",
        "start": f"{first}T{start}:00+02:00",
        "end": f"{DAY}T{end}:00+02:00",
        "value": value,
        "device": device,
    }


async def test_a_night_takes_the_watch_phases_and_the_iphone_bed(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    app = await _app(client, auth)
    night = [
        _sleep("N1", "23:00", "01:00", 3, WATCH),  # core
        _sleep("N2", "01:00", "02:00", 4, WATCH),  # deep
        _sleep("N3", "02:00", "03:00", 5, WATCH),  # REM
        _sleep("N4", "03:00", "03:10", 2, WATCH),  # awake
        _sleep("N5", "03:10", "06:40", 3, WATCH),  # core: 450 min asleep
        _sleep("P0", "22:50", "06:45", 0, "iPhone de Test"),  # in bed only
        _sleep("A1", "23:30", "07:30", 1, "Autre app de test"),  # 480 min
    ]
    sent = await client.post(URL, json={"samples": night}, headers=app)
    assert sent.json()["samples"] == 7, sent.text
    # the watch's phases, though the other app counted more sleep
    assert await _day(client, auth, "sleep.asleep") == 450
    assert await _day(client, auth, "sleep.deep") == 60
    assert await _day(client, auth, "sleep.core") == 330
    assert await _day(client, auth, "sleep.awake") == 10
    assert await _day(client, auth, "sleep.time_in_bed") == 475  # iPhone
    nights = await client.get(
        "/api/v1/sleep/nights",
        params={"start": DAY, "end": DAY, "missing": "false"},
        headers=auth,
    )
    view = nights.json()[0]
    assert (view["bedtime"], view["wake_time"]) == ("23:00", "06:40")
    assert view["awakenings"] == 1 and view["source"].endswith(WATCH)
    state = (await client.get(URL, headers=app)).json()
    assert state["samples"] == 7  # as sent: not the nights' totals
    # a night the watch did not record: the other recorder, never both
    watch = [s["uuid"] for s in night if s["device"] == WATCH]
    await client.post(URL, json={"deleted": watch}, headers=app)
    assert await _day(client, auth, "sleep.asleep") == 480
    assert await _day(client, auth, "sleep.deep") is None
    assert await _day(client, auth, "sleep.time_in_bed") == 475


async def test_workouts_are_kept_by_uuid_and_make_their_day(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    app = await _app(client, auth)
    walk = {
        "uuid": "W1",
        "activity": "walking",
        "start": f"{DAY}T18:00:00+02:00",
        "end": f"{DAY}T18:45:00+02:00",
        "energy_kcal": 210,
        "distance_km": 3.1,
    }
    for _ in range(2):  # sent twice: one workout
        sent = await client.post(URL, json={"workouts": [walk]}, headers=app)
        assert sent.json()["workouts"] == 1
    assert await _day(client, auth, "workout.count") == 1
    assert await _day(client, auth, "workout.total_min") == 45
    assert await _day(client, auth, "workout.distance") == 3.1
    listed = (await client.get("/api/v1/workouts", headers=auth)).json()
    kinds = [w["activity_type"] for w in listed]
    assert kinds == ["HKWorkoutActivityTypeWalking"]
    await client.post(URL, json={"deleted": ["W1"]}, headers=app)
    assert await _day(client, auth, "workout.count") is None


async def test_each_account_syncs_its_own_and_only_by_header(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    app = await _app(client, auth)
    await client.post(
        URL, json={"samples": [_hr("A1", "08:00", 60)]}, headers=app
    )
    theirs = await client.post(URL, json={"deleted": ["A1"]}, headers=member)
    assert theirs.json()["deleted"] == 0  # not their sample
    own = await client.post(
        URL, json={"samples": [_hr("A1", "09:00", 99)]}, headers=member
    )
    assert own.json()["samples"] == 1  # the same UUID, their own copy
    assert await _day(client, auth, "heart.rate") == 60
    assert (await client.get(URL, headers=member)).json()["samples"] == 1
    assert (await client.post(URL, json={})).status_code == 401
    token = app["Authorization"].split()[1]
    in_url = await client.post(f"{URL}?token={token}", json={})
    assert in_url.status_code == 401  # the header only
