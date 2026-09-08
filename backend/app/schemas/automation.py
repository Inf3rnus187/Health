"""Automation schemas (trigger → action rules, §7.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_TRIGGERS = {"nfc", "shortcut", "manual", "schedule", "api"}


class AutomationCreate(BaseModel):
    """A named trigger→action rule."""

    name: str = Field(min_length=1, max_length=120)
    trigger: str
    action: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("trigger")
    @classmethod
    def _known_trigger(cls, value: str) -> str:
        """Reject unknown trigger kinds."""
        if value not in _TRIGGERS:
            raise ValueError(f"invalid trigger: {value}")
        return value


class AutomationUpdate(BaseModel):
    """Mutable fields of an automation."""

    name: str | None = Field(default=None, max_length=120)
    action: dict[str, Any] | None = None
    is_active: bool | None = None


class AutomationOut(BaseModel):
    """Public projection of an automation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    trigger: str
    action: dict[str, Any]
    is_active: bool
    created_at: datetime
