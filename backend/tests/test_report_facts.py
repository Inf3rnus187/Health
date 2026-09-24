"""Reports that prove facts, and a fingerprint for authentic copies.

Habits with the days without data, before / after, doses, meals,
traceability.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.db import SessionFactory
from app.models.meal import Meal
from httpx import AsyncClient
from pypdf import PdfReader

TALLY = "/api/v1/sync/tally"
PARIS = ZoneInfo("Europe/Paris")


async def _tap(
    client: AsyncClient, auth: dict[str, str], day: str, n: float
) -> None:
    body = {"metric": "habit.cigarettes", "date_key": day, "amount": n}
    res = await client.post(TALLY, json=body, headers=auth)
    assert res.status_code == 200, res.text


async def _history(client: AsyncClient, auth: dict[str, str]) -> None:
    """Cigarettes: 20, 18, (nothing), 10, 0 (declared) on 2026-03-01..05."""
    for day, n in (("01", 20), ("02", 18), ("04", 10), ("05", 0)):
        await _tap(client, auth, f"2026-03-{day}", n)


async def test_habits_state_the_days_without_data_and_compare(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _history(client, auth)
    res = await client.get(
        "/api/v1/facts",
        params={"start": "2026-03-01", "end": "2026-03-05",
                "compare_from": "2026-03-04"},
        headers=auth,
    )  # fmt: skip
    body = res.json()
    (smoke,) = (h for h in body["habits"] if h["key"] == "habit.cigarettes")
    assert (smoke["days"], smoke["days_with_data"], smoke["days_without"]) == (
        5,
        4,
        1,
    )
    assert (smoke["total"], smoke["mean"]) == (48, 12)
    assert smoke["lowest"] == {"value": 0, "date": "2026-03-05"}
    assert smoke["highest"] == {"value": 20, "date": "2026-03-01"}
    compare = smoke["compare"]
    assert (compare["before"]["mean"], compare["after"]["mean"]) == (19, 5)
    assert compare["change_pct"] == -73.7
    (taps,) = (
        c
        for c in body["trace"]["counters"]
        if c["metric"] == "habit.cigarettes"
    )
    assert (taps["entries"], taps["later"], taps["same_day"]) == (4, 4, 0)
    assert taps["channels"] == {"site": 4}


async def _meal_read(user_email: str) -> None:
    """A meal read by the AI, as the worker leaves it."""
    from app.models.user import User
    from sqlalchemy import select

    async with SessionFactory() as session:
        user = await session.scalar(
            select(User).where(User.email == user_email)
        )
        assert user is not None
        at = datetime(2026, 3, 2, 12, 30, tzinfo=PARIS)
        session.add(Meal(
            user_id=user.id, eaten_at=at, date_key=at.date(),
            meal_type="lunch", description="riz et poulet",
            analysis_status="done",
            analysis={"score": 7, "totals": {"energy_kcal": 600,
                      "protein_g": 40, "sodium_mg": 500},
                      "items": [{"name": "Riz", "source": "étiquette",
                                 "grams": 125}]},
        ))  # fmt: skip
        await session.commit()


async def test_a_report_proves_and_can_be_verified(
    client: AsyncClient, auth: dict[str, str], member: dict[str, str]
) -> None:
    await _history(client, auth)
    await _meal_read("admin@example.com")
    body: dict[str, Any] = {
        "type": "clinical_pdf",
        "period_start": "2026-03-01",
        "period_end": "2026-03-05",
        "params": {"compare_from": "2026-03-04"},
    }
    made = await client.post("/api/v1/reports", json=body, headers=auth)
    report = (
        await client.get(f"/api/v1/reports/{made.json()['id']}", headers=auth)
    ).json()
    assert report["status"] == "ready" and len(report["sha256"]) == 64
    pdf = (
        await client.get(f"/api/v1/reports/{report['id']}/file", headers=auth)
    ).content
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    for words in ("Habitudes enregistr", "Cigarettes", "Avant le 2026-03-04",
                  "Alimentation", "Tra", report["id"],
                  "Empreinte des donn"):  # fmt: skip
        assert words in text, words
    url = "/api/v1/reports/verify"
    ok = await client.post(url, files={"file": ("r.pdf", pdf)}, headers=auth)
    assert ok.json()["authentic"] is True
    assert ok.json()["report"]["id"] == report["id"]
    changed = pdf[:-10] + b"0000000000"
    bad = await client.post(
        url, files={"file": ("r.pdf", changed)}, headers=auth
    )
    assert bad.json()["authentic"] is False
    other = await client.post(
        url, files={"file": ("r.pdf", pdf)}, headers=member
    )
    assert other.json()["authentic"] is False  # never someone else's


async def test_meals_and_doses_facts(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    await _meal_read("admin@example.com")
    treatment = await client.post(
        "/api/v1/treatments",
        json={"name": "Traitement A", "doses_per_day": 1,
              "start_date": "2026-03-01", "end_date": "2026-03-05"},
        headers=auth,
    )  # fmt: skip
    at = datetime(2026, 3, 2, 8, 0, tzinfo=PARIS).isoformat()
    await client.post(
        f"/api/v1/treatments/{treatment.json()['id']}/intakes",
        json={"taken_at": at},
        headers=auth,
    )
    res = await client.get(
        "/api/v1/facts",
        params={"start": "2026-03-01", "end": "2026-03-05"},
        headers=auth,
    )
    body = res.json()
    meals = body["meals"]
    assert (meals["meals"], meals["analysed"]) == (1, 1)
    assert meals["daily_means"]["energy_kcal"] == 600
    assert meals["scores"]["mean"] == 7
    assert meals["top_foods"] == [{"name": "Riz", "meals": 1, "grams": 125}]
    assert meals["sources"] == {"étiquette": 1}
    (dose,) = body["medications"]
    assert (dose["planned"], dose["taken"], dose["rate"]) == (5, 1, 20.0)
    assert body["trace"]["medications"]["later"] == 1
    assert timedelta(hours=3) > timedelta(0)
