"""Canonical vocabularies for the metric registry and measurements."""

from __future__ import annotations

DATA_TYPES: frozenset[str] = frozenset(
    {"int", "float", "bool", "enum", "time", "duration", "text", "score"}
)

#: Numeric data types stored in ``value_num``.
NUMERIC_TYPES: frozenset[str] = frozenset({"int", "float", "duration", "score"})

METRIC_SOURCES: frozenset[str] = frozenset(
    {"manual", "watch", "ppc", "ai", "script", "derived"}
)

AGGREGATIONS: frozenset[str] = frozenset({"avg", "sum", "min", "max", "last"})

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "daily_entry",
        "sleep",
        "ppc",
        "workout_block",
        "walk",
        "capture_session",
        "custom",
    }
)

#: ``domain.snake`` — e.g. ``sleep.spo2_min``.
METRIC_KEY_PATTERN = r"^[a-z][a-z0-9]*\.[a-z0-9_]+$"
