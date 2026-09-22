"""Validated metabolic / liver markers built from the user's latest data.

Photos show a visual trend; these published scores give the numbers a
doctor actually uses (waist-to-height ratio, BMI, FLI, FIB-4, HbA1c,
fasting glucose, TyG), each with its reference bands, the date of its
oldest input and the inputs still missing. Screening, not diagnosis.
"""

from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.measurement import Measurement
from app.models.metric import MetricDefinition
from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services import metabolic_catalog as cat
from app.services.apple_health.metrics_cache import MetricCache

_METRES_MAX = 3.0  # a height below 3 is in metres
_MG_DL_MIN = 20.0  # TG / glucose above 20 are in mg/dL
_MMOL_MIN = 3.0  # glucose between 3 and 20 is in mmol/L
_IFCC_MIN = 20.0  # HbA1c above 20 is in mmol/mol (IFCC)
_SENIOR_AGE = 65.0


class Value(NamedTuple):
    """Latest value of one input and its day."""

    value: float
    day: date


async def markers(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Every marker (value, level, interpretation) plus the profile."""
    inputs = await _latest(session, user_id)
    return {
        "markers": [_build(spec, inputs) for spec in cat.SPECS],
        "profile": _profile(inputs),
    }


async def save_profile(
    session: AsyncSession, user_id: str, fields: dict[str, float], day: date
) -> None:
    """Record waist / height / birth year (metrics created on first use)."""
    cache = MetricCache()
    items: list[MeasurementIn] = []
    for name, value in fields.items():
        spec = cat.PROFILE[name]
        await cache.id_for(session, spec)
        items.append(
            MeasurementIn(metric_key=spec.key, date_key=day, value=value)
        )
    if items:
        await measure.record_batch(session, user_id, items, source="manual")


async def _latest(session: AsyncSession, user_id: str) -> dict[str, Value]:
    """Latest value of each input (most recent source wins)."""
    keys = {key for group in cat.SOURCES.values() for key in group}
    result = await session.execute(
        select(
            MetricDefinition.key, Measurement.value_num, Measurement.date_key
        )
        .join(MetricDefinition, Measurement.metric_id == MetricDefinition.id)
        .where(
            Measurement.user_id == user_id,
            MetricDefinition.key.in_(keys),
            Measurement.value_num.is_not(None),
        )
        .order_by(Measurement.date_key)
    )
    found = {key: Value(float(num), day) for key, num, day in result.all()}
    out: dict[str, Value] = {}
    for name, group in cat.SOURCES.items():
        values = [found[key] for key in group if key in found]
        if values:
            out[name] = _normalize(name, max(values, key=lambda v: v.day))
    return out


def _normalize(name: str, value: Value) -> Value:
    """Bring common alternative units back to the formulas' units."""
    x = value.value
    if name == "height" and x < _METRES_MAX:
        x *= 100  # metres -> cm
    elif name in ("tg", "glucose") and x > _MG_DL_MIN:
        x /= 100  # mg/dL -> g/L
    elif name == "glucose" and x > _MMOL_MIN:
        x *= 0.18  # mmol/L -> g/L
    elif name == "hba1c" and x > _IFCC_MIN:
        x = 0.09148 * x + 2.152  # IFCC mmol/mol -> NGSP %
    return Value(x, value.day)


def _blank(spec: cat.Spec, missing: list[str]) -> dict[str, Any]:
    """A marker without a value (inputs missing or inconsistent)."""
    return {
        "key": spec.key,
        "label": spec.label,
        "unit": spec.unit,
        "reference": spec.reference,
        "missing": missing,
        "value": None,
        "date": None,
        "level": "missing",
        "interpretation": "Données manquantes",
    }


def _build(spec: cat.Spec, inputs: dict[str, Value]) -> dict[str, Any]:
    """Compute one marker, or report what is missing."""
    missing = [cat.LABELS[name] for name in spec.needs if name not in inputs]
    out = _blank(spec, missing)
    if missing:
        return out
    values = {name: inputs[name].value for name in spec.needs}
    try:
        value = spec.compute(values)
    except (ValueError, ZeroDivisionError):
        out["interpretation"] = "Valeurs incohérentes"
        return out
    band = _band(spec, values, value)
    out.update(
        value=round(value, spec.digits),
        date=_as_of(spec, inputs),
        level=band.level,
        interpretation=band.text,
    )
    return out


def _band(spec: cat.Spec, values: dict[str, float], value: float) -> cat.Band:
    """Reference band containing ``value`` (age-adjusted when defined)."""
    bands = spec.bands
    senior = "birth_year" in values and (
        cat.age(values["birth_year"]) >= _SENIOR_AGE
    )
    if spec.senior_bands is not None and senior:
        bands = spec.senior_bands
    return next(band for band in bands if value < band.below)


def _as_of(spec: cat.Spec, inputs: dict[str, Value]) -> str | None:
    """Date of the oldest time-varying input (the marker's freshness)."""
    days = [inputs[n].day for n in spec.needs if n not in cat.STATIC]
    return min(days).isoformat() if days else None


def _profile(inputs: dict[str, Value]) -> dict[str, Any]:
    """Current anthropometric profile for the form."""
    waist = inputs.get("waist")
    return {
        "waist_cm": waist.value if waist else None,
        "waist_date": waist.day.isoformat() if waist else None,
        "height_cm": _value(inputs, "height"),
        "weight_kg": _value(inputs, "weight"),
        "birth_year": _value(inputs, "birth_year"),
    }


def _value(inputs: dict[str, Value], name: str) -> float | None:
    """Plain value of an input, if known."""
    found = inputs.get(name)
    return found.value if found else None
