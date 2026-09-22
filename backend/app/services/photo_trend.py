"""Long-term evolution of the photo scores, per angle and criterion.

Only method-v2 analyses of photos that passed quality control count.
Several photos on one day collapse to their median; the displayed curve
is a 7-day rolling median and the trend is a Theil-Sen slope over the
last 90 days, reported only with enough data (≥ 8 days over ≥ 21 days):
day-to-day changes are noise, only weeks-long trends are interpretable.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo import Photo, PhotoAnalysis
from app.services import photo_method, robust_stats, weight_trend
from app.services.robust_stats import Point

ANGLES = ("face", "profil", "dos")
_MIN_DAYS = 8
_MIN_SPAN = 21
_SLOPE_WINDOW = 90
_EDGE = 7
_STABLE = 0.5  # score points per 30 days
_PAIR = 2  # a before/after difference needs two days

Row = tuple[Photo, dict[str, Any]]


async def trend(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Return the per-angle, per-criterion long-term evolution."""
    rows = await _valid_rows(session, user_id)
    totals = await _totals(session, user_id)
    weights = await weight_trend.series(session, user_id)
    return {
        "method_version": photo_method.METHOD,
        "weight": weight_trend.summary(weights),
        "angles": [
            _angle(angle, rows.get(angle, []), totals.get(angle, 0), weights)
            for angle in ANGLES
        ],
    }


async def _valid_rows(
    session: AsyncSession, user_id: str
) -> dict[str, list[Row]]:
    """Latest v2 analysis per photo, quality-passed and scored, by angle."""
    result = await session.execute(
        select(Photo, PhotoAnalysis)
        .join(PhotoAnalysis, PhotoAnalysis.photo_id == Photo.id)
        .where(
            Photo.user_id == user_id,
            PhotoAnalysis.prompt_version == photo_method.METHOD,
        )
        .order_by(PhotoAnalysis.created_at)
    )
    newest = {photo.id: (photo, a.raw_output) for photo, a in result.all()}
    grouped: dict[str, list[Row]] = {}
    for photo, output in newest.values():
        if output.get("quality", {}).get("ok") and output.get("scores"):
            grouped.setdefault(photo.angle, []).append((photo, output))
    for rows in grouped.values():
        rows.sort(key=lambda row: (row[0].date_key, row[0].taken_at))
    return grouped


async def _totals(session: AsyncSession, user_id: str) -> dict[str, int]:
    """Number of photos per angle, whatever their status."""
    result = await session.execute(
        select(Photo.angle, func.count())
        .where(Photo.user_id == user_id)
        .group_by(Photo.angle)
    )
    return {angle: int(count) for angle, count in result.all()}


def _angle(
    angle: str, rows: list[Row], total: int, weights: list[Point]
) -> dict[str, Any]:
    """Summary block for one angle."""
    return {
        "angle": angle,
        "baseline": _ref(rows[0][0], weights) if rows else None,
        "latest": _ref(rows[-1][0], weights) if rows else None,
        "photos_total": total,
        "photos_valid": len(rows),
        "criteria": [
            _criterion(c, rows) for c in photo_method.criteria_for(angle)
        ],
    }


def _criterion(
    criterion: photo_method.Criterion, rows: list[Row]
) -> dict[str, Any]:
    """Daily series, smoothed curve, slope and status for one criterion."""
    points = robust_stats.daily_median(
        [
            (photo.date_key, float(output["scores"][criterion.key]))
            for photo, output in rows
            if criterion.key in output["scores"]
        ]
    )
    span = (points[-1][0] - points[0][0]).days if points else 0
    enough = len(points) >= _MIN_DAYS and span >= _MIN_SPAN
    slope = _slope(points) if enough else None
    return {
        "key": criterion.key,
        "label": criterion.label,
        "points": _serial(points),
        "smoothed": _serial(robust_stats.rolling_median(points, _EDGE)),
        "n": len(points),
        "span_days": span,
        "slope_30d": slope,
        "baseline_delta": _baseline_delta(points),
        "status": _status(slope),
    }


def _slope(points: list[Point]) -> float | None:
    """Theil-Sen slope over the last 90 days, in points per 30 days."""
    start = points[-1][0] - timedelta(days=_SLOPE_WINDOW)
    per_day = robust_stats.theil_sen([p for p in points if p[0] >= start])
    return None if per_day is None else round(per_day * 30, 2)


def _baseline_delta(points: list[Point]) -> float | None:
    """Median of the last 7 days minus median of the first 7 days."""
    if len(points) < _PAIR:
        return None
    first, last = points[0][0], points[-1][0]
    edge = timedelta(days=_EDGE - 1)
    early = robust_stats.window_median(points, first, first + edge)
    late = robust_stats.window_median(points, last - edge, last)
    if early is None or late is None:
        return None
    return round(late - early, 2)


def _status(slope: float | None) -> str:
    """Interpretation (scores: lower = less abdominal fat = better)."""
    if slope is None:
        return "insufficient"
    if slope <= -_STABLE:
        return "improving"
    if slope >= _STABLE:
        return "worsening"
    return "stable"


def _ref(photo: Photo, weights: list[Point]) -> dict[str, Any]:
    """Photo reference for the before/after view, with that day's weight."""
    weight = photo.linked_weight
    if weight is None:
        weight = weight_trend.nearest(weights, photo.date_key)
    return {
        "photo_id": photo.id,
        "date": photo.date_key.isoformat(),
        "weight": None if weight is None else round(weight, 1),
    }


def _serial(points: list[Point]) -> list[dict[str, Any]]:
    """JSON-friendly series."""
    return [{"date": d.isoformat(), "value": round(v, 2)} for d, v in points]
