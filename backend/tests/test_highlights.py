"""The most significant days: continuous sessions, days off worked, spans."""

from __future__ import annotations

from httpx import AsyncClient

WORK = "/api/v1/work"


async def test_the_days_that_stand_out_come_first(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    for start, end, note in (
        ("2026-04-02T12:01", "2026-04-03T21:22", "GPS, taxi aller retour"),
        ("2026-04-04T12:16", "2026-04-04T21:18", ""),  # a Saturday
        ("2026-04-05T00:10", "2026-04-05T20:25", ""),  # a Sunday
        ("2026-04-06T07:00", "2026-04-06T18:00", ""),  # Easter Monday
        ("2026-04-07T09:00", "2026-04-07T17:00", ""),  # an ordinary day
    ):
        made = await client.post(
            f"{WORK}/sessions",
            json={"start_at": start, "end_at": end, "note": note},
            headers=auth,
        )
        assert made.status_code == 201, made.text
    health = await client.get(
        f"{WORK}/health",
        params={"start": "2026-04-01", "end": "2026-04-10"},
        headers=auth,
    )
    days = health.json()["highlights"]
    assert [d["date"] for d in days] == [
        "2026-04-02", "2026-04-05", "2026-04-06", "2026-04-04",
    ]  # fmt: skip
    first = days[0]
    assert (first["arrival"], first["departure"]) == ("12:01", "21:22 +1")
    assert first["flags"][0] == "session continue de 33 h 21, nuit comprise"
    assert first["notes"] == ["GPS, taxi aller retour"]
    sunday = days[1]["flags"]
    assert "amplitude 20 h 15 > 13 h (repos de 11 h impossible)" in sunday
    assert "dimanche travaillé" in sunday
    assert "jour férié travaillé" in days[2]["flags"]
    assert days[3]["flags"] == ["samedi travaillé", "fin après 21 h"]
    report = await client.post(
        "/api/v1/reports",
        json={"type": "work_health", "period_start": "2026-04-01",
              "period_end": "2026-04-10"},
        headers=auth,
    )  # fmt: skip
    assert report.json()["status"] == "ready"
