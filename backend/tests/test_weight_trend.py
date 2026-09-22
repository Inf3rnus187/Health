"""Weight history in the long-term follow-up (trend, changes, milestones)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from app.services import weight_trend
from httpx import AsyncClient

_START = date(2026, 6, 1)


def _losing(days: int = 60) -> list[tuple[date, float]]:
    """110 kg, then -0.1 kg a day."""
    return [(_START + timedelta(days=i), 110.0 - 0.1 * i) for i in range(days)]


def test_empty_history_has_no_summary() -> None:
    assert weight_trend.summary([]) is None


def test_losing_weight_trend_and_milestones() -> None:
    out = weight_trend.summary(_losing())
    assert out is not None
    assert out["latest"] == {"value": 104.1, "date": "2026-07-30"}
    assert out["status"] == "losing"
    assert out["slope_30d"] == pytest.approx(-3.0, abs=0.05)
    month = out["changes"][0]
    assert month["label"] == "1 mois"
    assert month["delta"] == pytest.approx(-3.0, abs=0.05)
    assert out["changes"][2]["delta"] is None  # no weigh-in a year ago
    assert out["peak"]["value"] == pytest.approx(109.9, abs=0.2)
    reached = [m["percent"] for m in out["milestones"] if m["reached"]]
    assert reached == [5]


def test_short_history_is_insufficient() -> None:
    out = weight_trend.summary(_losing(5))
    assert out is not None
    assert out["status"] == "insufficient"
    assert out["slope_30d"] is None


def test_nearest_weigh_in() -> None:
    points = [(_START, 100.0), (_START + timedelta(days=10), 99.0)]
    assert weight_trend.nearest(points, _START + timedelta(days=2)) == 100.0
    assert weight_trend.nearest(points, _START + timedelta(days=5)) is None


async def test_trend_endpoint_includes_weight(
    client: AsyncClient, auth: dict[str, str]
) -> None:
    items = [
        {"metric_key": "body.weight", "date_key": d.isoformat(), "value": kg}
        for d, kg in _losing(30)
    ]
    resp = await client.post(
        "/api/v1/measurements", json={"items": items}, headers=auth
    )
    assert resp.status_code in {200, 201}
    trend = (await client.get("/api/v1/evolution/trend", headers=auth)).json()
    assert trend["weight"]["latest"]["value"] == pytest.approx(107.1)
    assert trend["weight"]["n"] == 30
