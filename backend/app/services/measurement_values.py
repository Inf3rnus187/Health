"""Route a raw value into the right typed column and validate it.

Keeps the polymorphic value handling (§5.2) in one place so the
persistence service stays about persistence.
"""

from __future__ import annotations

from datetime import time
from typing import Any

from app.core.constants import NUMERIC_TYPES
from app.core.errors import InvalidInputError
from app.models.metric import MetricDefinition


def columns_for(metric: MetricDefinition, value: Any) -> dict[str, Any]:
    """Return the typed-column kwargs for ``value`` under ``metric``."""
    data_type = metric.data_type
    if data_type in NUMERIC_TYPES:
        return {"value_num": _to_float(metric, value)}
    if data_type == "bool":
        return {"value_bool": bool(value)}
    if data_type == "time":
        return {"value_time": _to_time(metric, value)}
    if data_type in {"text", "enum"}:
        return {"value_text": str(value)}
    return {"value_json": _to_json(value)}


def validate(metric: MetricDefinition, value: Any) -> None:
    """Validate ``value`` against the metric's rules."""
    if metric.data_type == "enum":
        _check_enum(metric, value)
    if metric.data_type in NUMERIC_TYPES:
        _check_bounds(metric, value)


def _to_float(metric: MetricDefinition, value: Any) -> float:
    """Coerce ``value`` to ``float`` or raise a domain error."""
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f"{metric.key}: expected a number") from exc


def _to_time(metric: MetricDefinition, value: Any) -> time:
    """Coerce ``value`` to a ``time`` or raise a domain error."""
    if isinstance(value, time):
        return value
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise InvalidInputError(f"{metric.key}: expected HH:MM") from exc


def _to_json(value: Any) -> dict[str, Any]:
    """Wrap non-object values so the JSON column stays an object."""
    if isinstance(value, dict):
        return value
    return {"value": value}


def _check_enum(metric: MetricDefinition, value: Any) -> None:
    """Ensure ``value`` is one of the metric's enum options."""
    options = metric.enum_options or []
    if value not in options:
        raise InvalidInputError(
            f"{metric.key}: '{value}' is not an allowed option"
        )


def _check_bounds(metric: MetricDefinition, value: Any) -> None:
    """Ensure a numeric ``value`` respects min/max bounds."""
    num = _to_float(metric, value)
    if metric.min_value is not None and num < metric.min_value:
        raise InvalidInputError(f"{metric.key}: below minimum")
    if metric.max_value is not None and num > metric.max_value:
        raise InvalidInputError(f"{metric.key}: above maximum")
