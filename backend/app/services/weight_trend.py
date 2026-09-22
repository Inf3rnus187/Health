"""Body-weight history for the long-term abdominal / liver follow-up.

Uses every stored weigh-in (Apple Health, Health Auto Export, the web
form…): daily median, 7-day rolling median, Theil-Sen slope over the
last 90 days, changes over 1 / 3 / 12 months and the loss from the
12-month peak against the weight-loss thresholds of the EASL-EASD-EASO
MASLD guidelines (5 / 7-10 %) and the DiRECT trial (~15 %).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.services import robust_stats as rs
from app.services.robust_stats import Point

_KEY = "body.weight"
_WINDOW = 365
_EDGE = 7
_NEAR = 3  # photo ↔ weigh-in tolerance, days
_MIN_DAYS = 8
_MIN_SPAN = 21
_SLOPE_WINDOW = 90
_STABLE = 0.5  # kg per 30 days

_HORIZONS = ((30, "1 mois"), (90, "3 mois"), (365, "1 an"))
_MILESTONES = (
    (5, "Diminue la graisse du foie"),
    (7, "Améliore l'inflammation du foie (stéatohépatite)"),
    (10, "Peut faire régresser la fibrose du foie"),
    (15, "Rémission possible d'un diabète de type 2 récent"),
)


async def series(session: AsyncSession, user_id: str) -> list[Point]:
    """Every day with a weigh-in, oldest first (kg)."""
    result = await session.execute(
        select(Measurement.date_key, Measurement.value_num)
        .join(MetricDefinition, Measurement.metric_id == MetricDefinition.id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key == _KEY,
            Measurement.value_num.is_not(None),
        )
        .order_by(Measurement.date_key)
    )
    return rs.daily_median([(day, float(kg)) for day, kg in result.all()])


def summary(points: list[Point]) -> dict[str, Any] | None:
    """Latest weight, 12-month curve, trend, changes and milestones."""
    if not points:
        return None
    last = points[-1][0]
    recent = [p for p in points if p[0] > last - timedelta(days=_WINDOW)]
    smoothed = rs.rolling_median(recent, _EDGE)
    span = (recent[-1][0] - recent[0][0]).days
    enough = len(recent) >= _MIN_DAYS and span >= _MIN_SPAN
    slope = _slope(recent) if enough else None
    return {
        "latest": _dated(points[-1]),
        "first": _dated(points[0]),
        "current": round(smoothed[-1][1], 1),
        "points": _serial(recent),
        "smoothed": _serial(smoothed),
        "n": len(recent),
        "span_days": span,
        "slope_30d": slope,
        "status": _status(slope),
        "changes": [_change(points, d, label) for d, label in _HORIZONS],
        **_peak(smoothed),
    }


def nearest(points: list[Point], day: date) -> float | None:
    """Weigh-in closest to ``day`` (within a few days), if any."""
    close = [p for p in points if abs((p[0] - day).days) <= _NEAR]
    if not close:
        return None
    return min(close, key=lambda p: abs((p[0] - day).days))[1]


def _slope(points: list[Point]) -> float | None:
    """Theil-Sen slope over the last 90 days, kg per 30 days."""
    start = points[-1][0] - timedelta(days=_SLOPE_WINDOW)
    per_day = rs.theil_sen([p for p in points if p[0] >= start])
    return None if per_day is None else round(per_day * 30, 2)


def _status(slope: float | None) -> str:
    """Direction of the weight trend."""
    if slope is None:
        return "insufficient"
    if slope <= -_STABLE:
        return "losing"
    if slope >= _STABLE:
        return "gaining"
    return "stable"


def _change(points: list[Point], days: int, label: str) -> dict[str, Any]:
    """Median of the last week vs the median of the week ``days`` ago."""
    last = points[-1][0]
    week = timedelta(days=_EDGE - 1)
    target = last - timedelta(days=days)
    now = rs.window_median(points, last - week, last)
    then = rs.window_median(points, target - week, target)
    out: dict[str, Any] = {"label": label, "delta": None, "percent": None}
    if now is not None and then:
        out["delta"] = round(now - then, 1)
        out["percent"] = round((now - then) / then * 100, 1)
    return out


def _peak(smoothed: list[Point]) -> dict[str, Any]:
    """12-month peak (smoothed) and the loss since, vs the milestones."""
    day, top = max(smoothed, key=lambda p: p[1])
    loss = max(0.0, (top - smoothed[-1][1]) / top * 100)
    return {
        "peak": {"value": round(top, 1), "date": day.isoformat()},
        "loss_from_peak_pct": round(loss, 1),
        "milestones": [
            {"percent": pct, "label": text, "reached": loss >= pct}
            for pct, text in _MILESTONES
        ],
    }


def _dated(point: Point) -> dict[str, Any]:
    """A weigh-in as ``{value, date}``."""
    return {"value": round(point[1], 1), "date": point[0].isoformat()}


def _serial(points: list[Point]) -> list[dict[str, Any]]:
    """JSON-friendly series."""
    return [{"date": d.isoformat(), "value": round(v, 2)} for d, v in points]
