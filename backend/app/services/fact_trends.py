"""Facts from long series: key indicators and the photo trend."""

from __future__ import annotations

from datetime import date, timedelta
from statistics import fmean
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.services import metric_overview
from app.services.fact_format import Line, day, num

#: Apple Health / hub indicators summarised for the synthesis.
INDICATORS = (
    "rest.hr",
    "heart.hrv",
    "body.spo2",
    "body.resp_rate",
    "vitals.bp_systolic",
    "vitals.bp_diastolic",
    "activity.steps",
    "activity.exercise_min",
    "sleep.asleep",
    "fitness.vo2max",
    "habit.cigarettes",
    "ppc.ahi",
    "ppc.hours_used",
    "state.fatigue",
)
_WINDOW = 30
_MIN_DAYS = 3  # values needed in a 30-day window to report its mean
_BACK = (("30 jours avant", 30), ("il y a un an", 365))
Series = list[tuple[date, float]]


async def indicators(session: AsyncSession, user_id: str) -> list[Line]:
    """Key indicators: last 30 days vs the 30 before and a year ago."""
    out: list[Line] = []
    for key in INDICATORS:
        try:
            found = await metric_overview.overview(session, user_id, key, 400)
        except NotFoundError:
            continue
        text = _indicator(found)
        if text:
            out.append(("Indicateurs suivis", text))
    return out


def photos(found: dict[str, Any]) -> list[Line]:
    """Photo criteria with a reliable long-term trend."""
    out: list[Line] = []
    for angle in found["angles"]:
        for crit in angle["criteria"]:
            if crit["slope_30d"] is None:
                continue
            text = (
                f"Photos de {angle['angle']} — {crit['label']} (score 0-10) :"
                f" tendance {num(crit['slope_30d'])} point par 30 jours sur "
                f"{crit['span_days']} jours ({crit['n']} jours notés)"
            )
            if crit["baseline_delta"] is not None:
                delta = num(crit["baseline_delta"])
                text += f", écart avec la photo de référence {delta}"
            out.append(("Photos (méthode v2)", text))
    return out


def _indicator(found: dict[str, Any]) -> str | None:
    """One indicator's recent mean and its comparisons."""
    series: Series = [
        (date.fromisoformat(p["date"]), p["value"]) for p in found["series"]
    ]
    if not series:
        return None
    last = series[-1][0]
    now = _mean(series, last, 0)
    if now is None:
        return None
    unit = f" {found['unit']}" if found["unit"] else ""
    text = (
        f"{found['label']} : moyenne des 30 derniers jours "
        f"{num(now)}{unit} (au {day(last)})"
    )
    for label, back in _BACK:
        then = _mean(series, last, back)
        if then is not None:
            text += f" ; {label} {num(then)}{unit}"
    return text


def _mean(series: Series, last: date, back: int) -> float | None:
    """Mean over the 30 days ending ``back`` days before ``last``."""
    end = last - timedelta(days=back)
    start = end - timedelta(days=_WINDOW)
    values = [v for d, v in series if start < d <= end]
    return fmean(values) if len(values) >= _MIN_DAYS or back == 0 else None
