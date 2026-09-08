"""Metric-definition schemas (the dynamic registry contract)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.core.constants import (
    AGGREGATIONS,
    DATA_TYPES,
    METRIC_KEY_PATTERN,
    METRIC_SOURCES,
)


class MetricCreate(BaseModel):
    """Payload to register a new metric without a migration."""

    key: str = Field(pattern=METRIC_KEY_PATTERN, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    domain: str = Field(min_length=1, max_length=40)
    data_type: str
    unit: str | None = None
    source: str = "manual"
    enum_options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    aggregation_hint: str = "avg"
    formula: str | None = None

    @field_validator("data_type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        """Reject unknown data types."""
        if value not in DATA_TYPES:
            raise ValueError(f"invalid data_type: {value}")
        return value

    @field_validator("source")
    @classmethod
    def _known_source(cls, value: str) -> str:
        """Reject unknown sources."""
        if value not in METRIC_SOURCES:
            raise ValueError(f"invalid source: {value}")
        return value

    @field_validator("aggregation_hint")
    @classmethod
    def _known_agg(cls, value: str) -> str:
        """Reject unknown aggregation hints."""
        if value not in AGGREGATIONS:
            raise ValueError(f"invalid aggregation_hint: {value}")
        return value


class MetricUpdate(BaseModel):
    """Mutable fields of a metric (key/type/domain are immutable)."""

    label: str | None = Field(default=None, max_length=160)
    unit: str | None = None
    enum_options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    aggregation_hint: str | None = None
    formula: str | None = None
    is_active: bool | None = None

    @field_validator("aggregation_hint")
    @classmethod
    def _known_agg(cls, value: str | None) -> str | None:
        """Reject unknown aggregation hints when provided."""
        if value is not None and value not in AGGREGATIONS:
            raise ValueError(f"invalid aggregation_hint: {value}")
        return value


class MetricOut(BaseModel):
    """Public projection of a metric definition."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    label: str
    domain: str
    data_type: str
    unit: str | None
    source: str
    enum_options: list[Any] | None
    min_value: float | None
    max_value: float | None
    aggregation_hint: str
    formula: str | None
    is_active: bool
    created_at: datetime
