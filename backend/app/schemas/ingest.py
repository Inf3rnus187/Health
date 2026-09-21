"""Ingestion schemas: generic samples and mapping management."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.constants import METRIC_KEY_PATTERN


class IngestSample(BaseModel):
    """One incoming sample; keyed by metric_key or an external type."""

    value: Any
    metric_key: str | None = None
    healthkit_type: str | None = None
    unit: str | None = None
    ts: datetime | None = None

    @model_validator(mode="after")
    def _require_key(self) -> IngestSample:
        """Require at least one way to identify the metric."""
        if not self.metric_key and not self.healthkit_type:
            raise ValueError("metric_key or healthkit_type is required")
        return self


class IngestPayload(BaseModel):
    """A dated batch of samples (Apple Watch / CPAP)."""

    date_key: date
    samples: list[IngestSample] = Field(min_length=1, max_length=500)


class IngestResult(BaseModel):
    """Outcome of an ingestion: counts and unresolved keys."""

    recorded: int
    skipped: list[str]


class HealthSyncPayload(BaseModel):
    """Flat ``{healthkit_type: value}`` map sent by the iPhone Shortcut."""

    date_key: date | None = None
    metrics: dict[str, Any] = Field(min_length=1, max_length=500)


class TallyPayload(BaseModel):
    """One-tap counter increment (café, cigarette, bouteille d'eau)."""

    metric: str = Field(min_length=1, max_length=80)
    amount: float = 1.0
    date_key: date | None = None


class TallyResult(BaseModel):
    """The metric's running daily total after the increment."""

    metric: str
    date_key: date
    total: float


class MappingCreate(BaseModel):
    """Create/override an external-key → metric-key mapping."""

    source: str
    external_key: str = Field(min_length=1, max_length=128)
    metric_key: str = Field(pattern=METRIC_KEY_PATTERN, max_length=80)

    @field_validator("source")
    @classmethod
    def _known_source(cls, value: str) -> str:
        """Only watch/ppc sources have external mappings."""
        if value not in {"watch", "ppc"}:
            raise ValueError("source must be 'watch' or 'ppc'")
        return value


class MappingOut(BaseModel):
    """Public projection of an ingest mapping."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    external_key: str
    metric_key: str
    user_id: str | None
    created_at: datetime
