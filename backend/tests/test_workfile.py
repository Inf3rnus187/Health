"""Work file: Shortcut logs, absences, evidence, nights, the big report."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.core.db import SessionFactory
from app.models import HealthSample, User
from app.services import timed_entries
from app.services.apple_health.spec import SLEEP_RAW
from httpx import AsyncClient
from sqlalchemy import select

LOGS = "/api/v1/logs/import"

# Same layout as the iPhone Shortcut history files ("N | date time").
_IN = "1 | 02/03/2026 08:10\n2 | 03/03/2026 08:05\n3 | 03/03/2026 08:40\n"
_OUT = "1 | 02/03/2026 12:00\n2 | 02/03/2026 18:30\n3 | 03/03/2026 17:00\n"
_SMOKE = "1 | 02/03/2026 07:40\n2 | 02/03/2026 12:10\n3 | 04/03/2026 09:00\n"


async def _logs(
    client: AsyncClient, auth: dict[str, str], dry_run: bool
) -> Any:
    files = [
        ("files", ("Embauche.txt", _IN.encode(), "text/plain")),
        ("files", ("Debauche.txt", _OUT.encode(), "text/plain")),
        ("files", ("Cigarettes.txt", _SMOKE.encode(), "text/plain")),
    ]
    res = await client.post(
        LOGS, files=files, params={"dry_run": str(dry_run).lower()},
        headers=auth,
    )  # fmt: skip
    return res.json()


async def test_shortcut_logs_are_paired_and_counted(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/measurements",
        json={"items": [{"metric_key": "habit.cigarettes",
                         "date_key": "2026-03-04", "value": 5}]},
        headers=auth,
    )  # fmt: skip
    preview = await _logs(client, auth, True)
    keys = [f["key"] for f in preview["files"]]
    assert keys == ["work.start", "work.end", "habit.cigarettes"]
    work = preview["work"]
    # 02/03: 08:10-12:00 then a departure alone at 18:30 (return not
    # logged); 03/03: the second clock-in is a repeat, 08:05-17:00.
    assert (work["complete"], work["missing_start"]) == (2, 1)
    assert work["notes"][0]["reason"].startswith("embauche répétée")
    assert preview["habit.cigarettes"] == {
        "days": 2, "events": 3, "set": 1, "raised": 0, "kept": 1,
    }  # fmt: skip
    done = await _logs(client, auth, False)
    assert done["work"]["stored"] == 3
    again = await _logs(client, auth, False)
    listed = await client.get(
        "/api/v1/work/sessions",
        params={"start": "2026-03-01", "end": "2026-03-05"},
        headers=auth,
    )
    assert len(listed.json()) == 3 and again["work"]["stored"] == 3
    lone = next(s for s in listed.json() if s["status"] == "missing_start")
    fixed = await client.put(
        f"/api/v1/work/sessions/{lone['id']}",
        json={"start_at": "2026-03-02T13:30"},
        headers=auth,
    )
    assert fixed.json()["hours"] == 5.0 and fixed.json()["source"] == "edited"


async def test_absences_and_evidence_with_fingerprint(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    leave = await client.post(
        "/api/v1/absences",
        json={"start_date": "2026-03-09", "end_date": "2026-03-18",
              "cause": "Épuisement, fièvre"},
        headers=auth,
    )  # fmt: skip
    assert leave.status_code == 201
    shot = b"\x89PNG fake screenshot bytes"
    proof = await client.post(
        "/api/v1/evidence",
        data={"occurred_at": "2026-03-15T11:20", "kind": "appel",
              "title": "Appels du chef", "count": "12"},
        files={"file": ("appels.png", shot, "image/png")},
        headers=auth,
    )  # fmt: skip
    body = proof.json()
    assert body["sha256"] == hashlib.sha256(shot).hexdigest()
    assert body["occurred_at"].startswith("2026-03-15T10:20")  # 11:20 Paris
    got = await client.get(f"/api/v1/evidence/{body['id']}/file", headers=auth)
    assert got.content == shot
    worked = await client.post(
        "/api/v1/work/sessions",
        json={"start_at": "2026-03-15T17:00", "end_at": "2026-03-16T03:00"},
        headers=auth,
    )
    assert worked.json()["hours"] == 10.0  # Sunday, sick, 17:00 → 03:00
    health = await client.get(
        "/api/v1/work/health",
        params={"start": "2026-03-01", "end": "2026-03-31"},
        headers=auth,
    )
    (absence,) = health.json()["absences"]
    assert absence["worked_days"] == ["2026-03-15"]
    assert (absence["calls"], absence["calls_on_sundays"]) == (12, 12)
    assert health.json()["legal"]["sundays"] == ["2026-03-15"]
    assert health.json()["legal"]["night_hours"] == 6.0


async def _sleep(user_id: str, parts: list[tuple[str, str, str]]) -> None:
    async with SessionFactory() as session:
        metric = await timed_entries.metric_for(session, SLEEP_RAW)
        for start, end, stage in parts:
            session.add(
                HealthSample(
                    user_id=user_id, metric_id=metric.id,
                    start_at=datetime.fromisoformat(start).astimezone(UTC),
                    end_at=datetime.fromisoformat(end).astimezone(UTC),
                    value_text=stage, source="apple", device="Watch",
                )
            )  # fmt: skip
        await session.commit()


async def test_nights_count_awakenings_and_blocks(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalar_one()
    await _sleep(
        user.id,
        [
            ("2026-03-02T23:30+01:00", "2026-03-03T01:30+01:00", "asleepCore"),
            ("2026-03-03T01:30+01:00", "2026-03-03T01:50+01:00", "awake"),
            ("2026-03-03T01:50+01:00", "2026-03-03T02:30+01:00", "asleepDeep"),
            ("2026-03-03T04:00+01:00", "2026-03-03T06:00+01:00", "asleepREM"),
        ],
    )
    nights = await client.get(
        "/api/v1/sleep/nights",
        params={"start": "2026-03-03", "end": "2026-03-04"},
        headers=auth,
    )
    missing, night = nights.json()
    assert missing == {"wake_day": "2026-03-04", "missing": True}
    assert night["asleep_min"] == 280.0  # 2 h + 40 min + 2 h
    assert (night["awakenings"], night["blocks"]) == (1, 2)
    assert (night["bedtime"], night["wake_time"]) == ("23:30", "06:00")
    typed = await client.post(
        "/api/v1/sleep/nights",
        json={"bedtime": "2026-03-03T23:00", "wake_time": "2026-03-04T05:00",
              "awakenings": 3},
        headers=auth,
    )  # fmt: skip
    assert typed.json()["asleep_min"] == 360


async def test_work_health_report_is_a_pdf(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/work/sessions",
        json={"start_at": "2026-03-02T08:00", "end_at": "2026-03-02T21:30"},
        headers=auth,
    )
    await client.post(
        "/api/v1/work/sessions",
        json={"start_at": "2026-03-03T06:00", "end_at": "2026-03-03T15:00"},
        headers=auth,
    )
    health = await client.get(
        "/api/v1/work/health",
        params={"start": "2026-03-01", "end": "2026-03-07"},
        headers=auth,
    )
    legal = health.json()["legal"]
    assert legal["short_rests"] == [{"date": "2026-03-03", "rest_hours": 8.5}]
    assert legal["spread_over_13h"][0]["hours"] == 13.5
    report = await client.post(
        "/api/v1/reports",
        json={"type": "work_health", "period_start": "2026-03-01",
              "period_end": "2026-03-07"},
        headers=auth,
    )  # fmt: skip
    assert report.json()["status"] == "ready"
    pdf = await client.get(
        f"/api/v1/reports/{report.json()['id']}/file", headers=auth
    )
    assert pdf.content[:5] == b"%PDF-"


async def test_days_to_complete_come_with_their_context(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for day in ("02", "09"):  # two Mondays, 09:00-18:00: the usual times
        await client.post(
            "/api/v1/work/sessions",
            json={
                "start_at": f"2026-03-{day}T09:00",
                "end_at": f"2026-03-{day}T18:00",
            },
            headers=auth,
        )
    await client.post(
        "/api/v1/work/sessions",
        json={"start_at": "2026-03-16T09:10"},  # a Monday, never closed
        headers=auth,
    )
    await client.post(
        "/api/v1/evidence",
        data={"occurred_at": "2026-03-17T02:40", "kind": "taxi",
              "place": "Bureau", "amount": "30"},
        headers=auth,
    )  # fmt: skip
    todo = (await client.get("/api/v1/work/incomplete", headers=auth)).json()
    (day,) = todo
    context = day["context"]
    assert day["status"] == "missing_end" and context["missing"] == "end"
    assert context["has_proof"]
    assert context["evidence"][0]["time"] == "17/03 02:40"  # the next night
    assert context["usual"] == {
        "weekday": "lundi", "that_weekday": "18:00", "overall": "18:00",
    }  # fmt: skip
    stats = await client.get(
        "/api/v1/work/stats?start=2026-03-16&end=2026-03-16", headers=auth
    )
    assert stats.json()["open"] is None  # a forgotten clock-in: not "at work"


async def test_nights_since_the_first_one_known(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    async with SessionFactory() as session:
        user = (await session.execute(select(User))).scalar_one()
    await _sleep(
        user.id,
        [("2025-01-09T23:00+01:00", "2025-01-10T07:00+01:00", "asleepCore")],
    )
    listed = await client.get(
        "/api/v1/sleep/nights", params={"missing": "false"}, headers=auth
    )
    assert [n["wake_day"] for n in listed.json()] == ["2025-01-10"]
    everything = await client.get("/api/v1/sleep/nights", headers=auth)
    assert everything.json()[-1]["wake_day"] == "2025-01-10"  # not 30 days


async def test_days_off_leave_the_averages_and_lower_the_target(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """A week with sick days is not a short week of work."""
    days = [(f"2026-03-0{d}", 8) for d in range(2, 7)]  # full week: 40 h
    days += [(f"2026-03-{d}", 11) for d in (11, 12, 13)]  # after 2 sick days
    days.append(("2026-03-17", 2))  # a call-out during leave
    for day, hours in days:
        await client.post(
            "/api/v1/work/sessions",
            json={
                "start_at": f"{day}T08:00",
                "end_at": f"{day}T{8 + hours}:00",
            },
            headers=auth,
        )
    for start, end, kind in (
        ("2026-03-09", "2026-03-10", "arret_maladie"),
        ("2026-03-16", "2026-03-20", "conge"),
    ):
        await client.post(
            "/api/v1/absences",
            json={"start_date": start, "end_date": end, "kind": kind},
            headers=auth,
        )
    stats = (
        await client.get(
            "/api/v1/work/stats",
            params={"start": "2026-03-02", "end": "2026-03-22"},
            headers=auth,
        )
    ).json()
    assert stats["avg_week_hours"] == 40  # the full week only
    assert stats["full_weeks"] == 1
    assert stats["overtime_hours"] == 5  # legal: hours beyond 35 h
    assert stats["beyond_target_hours"] == 5 + 12 + 2  # 21 h, then 0 h
    sick, leave = stats["weeks"][1], stats["weeks"][2]
    assert (sick["absent_days"], sick["target"], sick["absence"]) == (
        2, 21, "arret",
    )  # fmt: skip
    assert (leave["hours"], leave["target"]) == (2, 0)
    assert [(a["kind"], a["days"]) for a in stats["absences"]] == [
        ("arret", 2), ("conge", 5),
    ]  # fmt: skip
    assert stats["worked_while_off"] == [
        {"date": "2026-03-17", "kind": "conge", "hours": 2.0}
    ]
    off_day = next(d for d in stats["days"] if d["date"] == "2026-03-09")
    assert (off_day["hours"], off_day["absence"]) == (0, "arret")
    week = next(p for p in stats["periods"] if p["days"] == 7)
    assert (week["absent_days"], week["week_average"]) == (5, None)
