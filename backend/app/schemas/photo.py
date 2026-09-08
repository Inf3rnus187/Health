"""Photo and analysis response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PhotoOut(BaseModel):
    """Public projection of a progress photo."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    angle: str
    date_key: date
    taken_at: datetime
    status: str
    linked_weight: float | None
    created_at: datetime


class PhotoAnalysisOut(BaseModel):
    """Public projection of an AI photo analysis."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    photo_id: str
    model: str
    prompt_version: str
    raw_output: dict[str, Any]
    derived_metrics: dict[str, Any] | None
    comparison_ref: str | None
    created_at: datetime


class PhotoComparison(BaseModel):
    """Two photos side by side with their analyses."""

    from_photo: PhotoOut
    to_photo: PhotoOut
    from_analysis: PhotoAnalysisOut | None
    to_analysis: PhotoAnalysisOut | None
