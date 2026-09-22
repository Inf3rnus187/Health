"""Validated metabolic / liver markers built from the user's data.

Photos show a visual trend; these published scores give the numbers a
doctor actually uses: FibroScan (direct liver fat / stiffness), then the
indirect scores (waist-to-height ratio, BMI, FLI, FIB-4, HbA1c, fasting
glucose, TyG). Each comes with its reference bands, the values used, the
inputs still missing and its history at every past lab / FibroScan date.
Screening, not diagnosis.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.measurement import MeasurementIn
from app.services import measurements as measure
from app.services import metabolic_catalog as cat
from app.services import metabolic_history, metabolic_inputs
from app.services.apple_health.metrics_cache import MetricCache
from app.services.metabolic_inputs import Series, Value


async def markers(session: AsyncSession, user_id: str) -> dict[str, Any]:
    """Every marker (value, level, history…) plus the profile."""
    series = await metabolic_inputs.load(session, user_id)
    current = metabolic_inputs.latest(series)
    return {
        "markers": [_build(spec, current, series) for spec in cat.SPECS],
        "profile": _profile(current),
    }


async def save_profile(
    session: AsyncSession, user_id: str, fields: dict[str, float], day: date
) -> None:
    """Record profile / FibroScan values (metrics created on first use)."""
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


def _blank(spec: cat.Spec, current: dict[str, Value]) -> dict[str, Any]:
    """A marker without a value, listing what was found and what lacks."""
    return {
        "key": spec.key,
        "label": spec.label,
        "unit": spec.unit,
        "reference": spec.reference,
        "missing": [cat.LABELS[n] for n in spec.needs if n not in current],
        "inputs": [_used(n, current[n]) for n in spec.needs if n in current],
        "value": None,
        "date": None,
        "level": "missing",
        "interpretation": "Données manquantes",
        "note": _note(spec, current),
        "history": [],
    }


def _build(
    spec: cat.Spec, current: dict[str, Value], series: Series
) -> dict[str, Any]:
    """Compute one marker, or report what is missing."""
    out = _blank(spec, current)
    out["history"] = metabolic_history.history(spec, series)
    if out["missing"]:
        return out
    values = {name: current[name].value for name in spec.needs}
    try:
        value = spec.compute(values)
    except (ValueError, ZeroDivisionError):
        out["interpretation"] = "Valeurs incohérentes"
        return out
    band = cat.band_for(spec, values, value)
    out.update(
        value=round(value, spec.digits),
        date=_as_of(spec, current),
        level=band.level,
        interpretation=band.text,
    )
    return out


def _note(spec: cat.Spec, current: dict[str, Value]) -> str | None:
    """Say when a direct FibroScan measure outranks an indirect score."""
    direct = current.get(spec.superseded_by or "")
    if direct is None:
        return None
    return (
        f"FibroScan du {direct.day.strftime('%d/%m/%Y')} disponible : "
        "mesure directe, plus fiable que cet indice calculé."
    )


def _used(name: str, found: Value) -> dict[str, Any]:
    """One input value as used in a formula (shown for transparency)."""
    return {
        "label": cat.LABELS[name],
        "value": round(found.value, 2),
        "unit": cat.UNITS[name],
        "date": None if name in cat.STATIC else found.day.isoformat(),
    }


def _as_of(spec: cat.Spec, current: dict[str, Value]) -> str | None:
    """Date of the oldest time-varying input (the marker's freshness)."""
    days = [current[n].day for n in spec.needs if n not in cat.STATIC]
    return min(days).isoformat() if days else None


def _profile(current: dict[str, Value]) -> dict[str, Any]:
    """Current anthropometric / FibroScan profile for the form."""
    waist = current.get("waist")
    return {
        "waist_cm": waist.value if waist else None,
        "waist_date": waist.day.isoformat() if waist else None,
        "height_cm": _value(current, "height"),
        "weight_kg": _value(current, "weight"),
        "birth_year": _value(current, "birth_year"),
        "cap_db_m": _value(current, "cap"),
        "lsm_kpa": _value(current, "lsm"),
    }


def _value(current: dict[str, Value], name: str) -> float | None:
    """Plain value of an input, if known."""
    found = current.get(name)
    return found.value if found else None
