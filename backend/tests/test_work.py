"""Work hours: clock in / out, sessions, stats, import, export, report."""

from __future__ import annotations

import json
from typing import Any

from app.services import work_parse
from httpx import AsyncClient

WORK = "/api/v1/work"
TALLY = "/api/v1/sync/tally"


async def _session(
    client: AsyncClient, auth: dict[str, str], start: str, end: str
) -> Any:
    body = {"start_at": start, "end_at": end}
    return await client.post(f"{WORK}/sessions", json=body, headers=auth)


async def _day(client: AsyncClient, auth: dict[str, str], key: str) -> Any:
    view = await client.get(f"/api/v1/metrics/{key}/overview", headers=auth)
    return view.json()["day"]


async def test_a_tap_clocks_in_then_out(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Same rule as every Shortcut: /sync/tally with {"metric": key}."""
    came = await client.post(TALLY, json={"metric": "work.start"}, headers=auth)
    assert came.json()["detail"].startswith("Embauche ")
    again = await client.post(
        TALLY, json={"metric": "work.start"}, headers=auth
    )
    assert again.status_code == 200  # a second GPS trigger is ignored
    left = await client.post(TALLY, json={"metric": "work.end"}, headers=auth)
    assert left.json()["detail"].startswith("Débauche ")
    listed = (await client.get(f"{WORK}/sessions", headers=auth)).json()
    assert len(listed) == 1 and listed[0]["end_at"] is not None
    alone = await client.post(TALLY, json={"metric": "work.end"}, headers=auth)
    assert "à compléter" in alone.json()["detail"]  # kept, not refused
    listed = (await client.get(f"{WORK}/sessions", headers=auth)).json()
    assert [s["status"] for s in listed] == ["missing_start", "complete"]


async def test_sessions_feed_the_daily_values(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    made = await _session(client, auth, "2026-03-02T08:00", "2026-03-02T12:00")
    await _session(client, auth, "2026-03-02T13:30", "2026-03-02T19:00")
    assert made.json()["hours"] == 4.0
    assert (await _day(client, auth, "work.hours"))["value"] == 9.5
    assert (await _day(client, auth, "work.start"))["value"] == 8.0
    assert (await _day(client, auth, "work.end"))["value"] == 19.0
    overlap = await _session(
        client, auth, "2026-03-02T11:00", "2026-03-02T14:00"
    )
    assert overlap.status_code == 422
    fixed = await client.put(
        f"{WORK}/sessions/{made.json()['id']}",
        json={"end_at": "2026-03-02T12:30"},
        headers=auth,
    )
    assert fixed.json()["hours"] == 4.5
    assert (await _day(client, auth, "work.hours"))["value"] == 10.0
    for row in (await client.get(
        f"{WORK}/sessions", params={"start": "2026-03-01", "end": "2026-03-03"},
        headers=auth,
    )).json():  # fmt: skip
        await client.delete(f"{WORK}/sessions/{row['id']}", headers=auth)
    assert await _day(client, auth, "work.hours") is None


async def test_stats_count_overtime_and_legal_limits(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for day in range(2, 7):  # Mon 2 → Fri 6 March 2026, 07:00-18:00 (11 h)
        await _session(
            client, auth, f"2026-03-0{day}T07:00", f"2026-03-0{day}T18:00"
        )
    stats = (
        await client.get(
            f"{WORK}/stats",
            params={"start": "2026-03-01", "end": "2026-03-31"},
            headers=auth,
        )
    ).json()
    assert stats["total_hours"] == 55.0 and stats["days_worked"] == 5
    assert stats["overtime_hours"] == 20.0  # 55 h - 35 h contract
    assert stats["days_over_10h"] == 5 and stats["weeks_over_48h"] == 1
    assert (stats["avg_start"], stats["avg_end"]) == ("07:00", "18:00")
    assert stats["weeks"][0]["week"] == "2026-W10"
    assert [p["label"] for p in stats["periods"]][0] == "7 jours"


_CSV = """Date;Embauche;Débauche
02/03/2026;08:12;17:30
03/03/2026;07:58;18:05
04/03/2026;08:00
n'importe quoi
"""
_SHORTCUT = """Embauche le 5 mars 2026 à 08:10
Débauche le 5 mars 2026 à 17:40
"""
_JSON = [
    {"date": "2026-03-09", "embauche": "08:00", "debauche": "16:00"},
    {"date": "2026-03-10", "type": "arrivée", "heure": "08:30"},
    {"date": "2026-03-10", "type": "départ", "heure": "17:00"},
]


async def _import(
    client: AsyncClient,
    auth: dict[str, str],
    name: str,
    data: bytes,
    dry_run: bool,
) -> Any:
    files = {"file": (name, data, "text/plain")}
    params = {"dry_run": str(dry_run).lower()}
    res = await client.post(
        f"{WORK}/import", files=files, params=params, headers=auth
    )
    return res.json()


async def test_import_past_logs_dry_run_then_for_real(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    csv_bytes = _CSV.encode()
    preview = await _import(client, auth, "pointage.csv", csv_bytes, True)
    assert (preview["sessions"], preview["stored"]) == (2, 0)
    assert preview["skipped_count"] == 1  # 04/03: one time, no end
    assert preview["preview"][0] == {
        "day": "2026-03-02",
        "start": "08:12",
        "end": "17:30",
    }
    listed = await client.get(f"{WORK}/sessions", headers=auth)
    assert listed.json() == []  # a dry run writes nothing
    done = await _import(client, auth, "pointage.csv", csv_bytes, False)
    assert done["stored"] == 2
    twice = await _import(client, auth, "pointage.csv", csv_bytes, False)
    assert twice["stored"] == 2  # same starts: updated, not doubled
    shortcut = await _import(client, auth, "log.txt", _SHORTCUT.encode(), False)
    assert shortcut["stored"] == 1 and shortcut["total_hours"] == 9.5
    records = json.dumps(_JSON).encode()
    from_json = await _import(client, auth, "export.json", records, False)
    assert from_json["stored"] == 2 and from_json["total_hours"] == 16.5
    stats = await client.get(
        f"{WORK}/stats",
        params={"start": "2026-03-01", "end": "2026-03-31"},
        headers=auth,
    )
    assert stats.json()["days_worked"] == 5


async def test_export_and_pdf_report(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _session(client, auth, "2026-03-02T08:00", "2026-03-02T17:00")
    period = {"start": "2026-03-01", "end": "2026-03-31"}
    csv_res = await client.get(
        f"{WORK}/export", params={**period, "level": "weeks"}, headers=auth
    )
    assert "semaine,lundi,heures" in csv_res.text
    assert "2026-W10,2026-03-02,9.0" in csv_res.text
    xlsx = await client.get(
        f"{WORK}/export",
        params={**period, "level": "sessions", "format": "xlsx"},
        headers=auth,
    )
    assert xlsx.content[:2] == b"PK"
    report = await client.post(
        "/api/v1/reports",
        json={
            "type": "work",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
        headers=auth,
    )
    assert report.json()["status"] == "ready"
    pdf = await client.get(
        f"/api/v1/reports/{report.json()['id']}/file", headers=auth
    )
    assert pdf.content[:5] == b"%PDF-"


def test_lines_are_read_whatever_their_layout() -> None:
    cases = {
        "2026-03-04T08:05:00+01:00 in": ["in"],
        "06/03/2026;22:00;06:00": ["in", "out"],  # night shift
        "Mar 8, 2026 at 8:12 AM arrived": ["in"],
        "08/03/2026 total 8h30": [],
    }
    for line, kinds in cases.items():
        events, _ = work_parse.read_line(line, 1)
        assert [e.kind for e in events] == kinds, line
    night, _ = work_parse.read_line("06/03/2026;22:00;06:00", 1)
    assert night[1].at.day == 7


async def test_remote_work_after_a_day_on_site(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """Back home, work goes on: a remote session on top of the day."""
    await _session(client, auth, "2026-03-02T08:00", "2026-03-02T18:00")
    remote = await client.post(
        f"{WORK}/sessions",
        json={"start_at": "2026-03-02T21:00", "end_at": "2026-03-02T23:30",
              "place": "remote"},
        headers=auth,
    )  # fmt: skip
    assert remote.status_code == 201, remote.text
    assert remote.json()["place"] == "remote"
    assert (await _day(client, auth, "work.hours"))["value"] == 12.5
    assert (await _day(client, auth, "work.remote_hours"))["value"] == 2.5
    assert (await _day(client, auth, "work.end"))["value"] == 23.5
    overlap = await client.post(
        f"{WORK}/sessions",
        json={"start_at": "2026-03-02T17:00", "end_at": "2026-03-02T19:00",
              "place": "remote"},
        headers=auth,
    )  # fmt: skip
    assert overlap.status_code == 422  # not at home and at the office
    stats = (
        await client.get(
            f"{WORK}/stats",
            params={"start": "2026-03-02", "end": "2026-03-08"},
            headers=auth,
        )
    ).json()
    assert (stats["remote_hours"], stats["remote_days"]) == (2.5, 1)
    assert stats["remote_after_site"] == ["2026-03-02"]
    assert stats["weeks"][0]["remote"] == 2.5


async def test_a_remote_clock_in_opens_its_own_session(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    """On site clocked in (the clock-out forgotten), then remote tonight."""
    clock = f"{WORK}/clock"
    await client.post(
        clock, json={"kind": "in", "at": "2026-03-02T08:00"}, headers=auth
    )
    home = await client.post(
        clock,
        json={"kind": "in", "at": "2026-03-02T21:00", "place": "remote"},
        headers=auth,
    )
    assert home.json()["place"] == "remote"
    done = await client.post(
        clock, json={"kind": "out", "at": "2026-03-02T23:00"}, headers=auth
    )
    assert (done.json()["place"], done.json()["hours"]) == ("remote", 2.0)
    march = {"start": "2026-03-01", "end": "2026-03-31"}
    listed = (
        await client.get(f"{WORK}/sessions", params=march, headers=auth)
    ).json()
    assert [(s["place"], s["status"]) for s in listed] == [
        ("remote", "complete"),
        ("site", "missing_end"),  # the office clock-out, to complete
    ]
    tap = await client.post(
        TALLY, json={"metric": "work.remote_start"}, headers=auth
    )
    assert tap.json()["detail"].startswith("Embauche à distance ")
