"""JSON Web Token creation and decoding for interactive sessions."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt

from app.core.config import get_settings
from app.models.base import utcnow

_settings = get_settings()


def _encode(sub: str, ttl: timedelta, kind: str, sid: str) -> str:
    """Encode a signed JWT for subject ``sub`` and session ``sid``."""
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": sub,
        "sid": sid,
        "type": kind,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, _settings.secret_key, _settings.jwt_algorithm)


def create_access_token(sub: str, sid: str) -> str:
    """Return a short-lived access token."""
    ttl = timedelta(minutes=_settings.access_token_ttl_min)
    return _encode(sub, ttl, "access", sid)


def create_refresh_token(sub: str, sid: str) -> str:
    """Return a long-lived refresh token bound to a session id."""
    ttl = timedelta(days=_settings.refresh_token_ttl_days)
    return _encode(sub, ttl, "refresh", sid)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising on invalid/expired tokens."""
    return jwt.decode(
        token,
        _settings.secret_key,
        algorithms=[_settings.jwt_algorithm],
    )
