"""API-token request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.scopes import ALL_SCOPES


class TokenCreate(BaseModel):
    """Request to mint a scoped API token."""

    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def _known_scopes(cls, value: list[str]) -> list[str]:
        """Reject scopes outside the canonical set."""
        unknown = sorted(set(value) - ALL_SCOPES)
        if unknown:
            raise ValueError(f"unknown scopes: {', '.join(unknown)}")
        return sorted(set(value))


class TokenOut(BaseModel):
    """Public projection of an API token (never the secret)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked: bool
    created_at: datetime


class TokenCreated(TokenOut):
    """Token projection plus the plaintext secret, shown once."""

    token: str
