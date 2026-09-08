"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Email/password credentials (plus TOTP code when MFA is on)."""

    email: EmailStr
    password: str = Field(min_length=1)
    otp: str | None = None


class RefreshRequest(BaseModel):
    """A refresh token presented to obtain a new token pair."""

    refresh_token: str


class TokenPair(BaseModel):
    """Access + refresh JWTs returned after login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """Public projection of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: str
    timezone: str
    unit_system: str
    created_at: datetime
