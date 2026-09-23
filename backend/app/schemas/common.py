"""Shared response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A simple human-readable message payload."""

    detail: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the API."""

    code: str
    detail: str


class IdsIn(BaseModel):
    """Items to delete at once (only the user's own; other ids ignored)."""

    ids: list[str] = Field(min_length=1, max_length=5000)


class EvidenceDeleteIn(IdsIn):
    """Proofs and traces to delete; ``meals``: their Journal meals too."""

    meals: bool = False


class Deleted(BaseModel):
    """How many items were deleted (and meals with them)."""

    deleted: int
    meals: int = 0
