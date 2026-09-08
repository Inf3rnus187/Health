"""Shared response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class Message(BaseModel):
    """A simple human-readable message payload."""

    detail: str


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the API."""

    code: str
    detail: str
