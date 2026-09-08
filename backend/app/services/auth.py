"""User authentication, refresh sessions and rotation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AuthError
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security import verify_password
from app.models.base import as_utc, utcnow
from app.models.session import AuthSession
from app.models.user import User
from app.schemas.auth import TokenPair
from app.services import mfa

_settings = get_settings()


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
    otp: str | None = None,
) -> User:
    """Return the active user matching the credentials (and MFA)."""
    user = await _user_by_email(session, email)
    if user is None or not user.is_active:
        raise AuthError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    if user.mfa_enabled and not mfa.verify_code(user, otp or ""):
        raise AuthError("MFA code required or invalid")
    return user


async def login(session: AsyncSession, user: User) -> TokenPair:
    """Open a refresh session and issue a fresh token pair."""
    auth = AuthSession(user_id=user.id, expires_at=_refresh_deadline())
    session.add(auth)
    await session.flush()
    return _issue(user.id, auth.id)


async def refresh(session: AsyncSession, token: str) -> TokenPair:
    """Rotate the presented refresh session and issue a new pair."""
    payload = _decode_refresh(token)
    current = await _active_session(session, payload["sid"], payload["sub"])
    current.revoked = True
    fresh = AuthSession(user_id=current.user_id, expires_at=_refresh_deadline())
    session.add(fresh)
    await session.flush()
    return _issue(current.user_id, fresh.id)


async def logout(session: AsyncSession, token: str) -> None:
    """Revoke the refresh session behind ``token`` (best effort)."""
    try:
        payload = decode_token(token)
    except PyJWTError:
        return
    auth = await session.get(AuthSession, payload.get("sid"))
    if auth is not None:
        auth.revoked = True


def _refresh_deadline() -> datetime:
    """Return the expiry timestamp for a new refresh session."""
    return utcnow() + timedelta(days=_settings.refresh_token_ttl_days)


def _issue(user_id: str, sid: str) -> TokenPair:
    """Build an access+refresh pair for ``user_id``/``sid``."""
    return TokenPair(
        access_token=create_access_token(user_id, sid),
        refresh_token=create_refresh_token(user_id, sid),
    )


async def _user_by_email(session: AsyncSession, email: str) -> User | None:
    """Return the user with the given email, if any."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def _decode_refresh(token: str) -> dict[str, Any]:
    """Decode a refresh JWT, raising :class:`AuthError` on failure."""
    try:
        payload = decode_token(token)
    except PyJWTError as exc:
        raise AuthError("Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Invalid refresh token")
    return payload


async def _active_session(
    session: AsyncSession, sid: str, sub: str
) -> AuthSession:
    """Return a live, non-revoked session or raise :class:`AuthError`."""
    auth = await session.get(AuthSession, sid)
    expired = auth is not None and as_utc(auth.expires_at) < utcnow()
    if auth is None or auth.revoked or auth.user_id != sub or expired:
        raise AuthError("Session expired or revoked")
    return auth
