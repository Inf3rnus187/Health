"""Event schemas (grouping context for related measurements)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import EVENT_TYPES


class EventCreate(BaseModel):
    """Payload to open an event (a day, a night, a workout block)."""

    type: str
    occurred_at: datetime | None = None
    date_key: date | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        """Reject unknown event types."""
        if value not in EVENT_TYPES:
            raise ValueError(f"invalid event type: {value}")
        return value


class EventOut(BaseModel):
    """Public projection of an event."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    occurred_at: datetime
    date_key: date
    meta: dict[str, Any]
    source: str
    created_at: datetime
