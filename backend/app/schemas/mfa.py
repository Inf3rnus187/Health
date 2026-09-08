"""MFA (TOTP) request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MfaSetupOut(BaseModel):
    """The provisioning secret and otpauth URI to add to an app."""

    secret: str
    otpauth_uri: str


class MfaVerify(BaseModel):
    """A TOTP code from the authenticator app."""

    code: str = Field(min_length=6, max_length=10)
