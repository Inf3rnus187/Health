"""Report request/response schemas (§11)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

_REPORT_TYPES = {
    "clinical_pdf",
    "synthesis",
    "work",
    "work_health",
    "csv",
    "json",
    "xlsx",
    "fhir",
}


class ReportCreate(BaseModel):
    """Request to generate a report over a period."""

    type: str
    period_start: date | None = None
    period_end: date | None = None
    params: dict[str, Any] | None = None

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        """Reject unknown report types."""
        if value not in _REPORT_TYPES:
            raise ValueError(f"invalid report type: {value}")
        return value


class ReportOut(BaseModel):
    """Public projection of a report job."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    period_start: date | None
    period_end: date | None
    status: str
    created_at: datetime
    summary: dict[str, Any] | None = None
