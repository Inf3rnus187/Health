"""Request dependencies: principal resolution and scope checks.

A *principal* is the authenticated caller — either an interactive user
(access JWT, implicitly full-scoped over their own data) or a machine
using a scoped API token.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AuthError, ForbiddenError
from app.core.jwt import decode_token
from app.core.scopes import ALL_SCOPES
from app.core.security import hash_token
from app.models.base import as_utc, utcnow
from app.models.token import ApiToken
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller and its effective scopes."""

    user: User
    scopes: frozenset[str]
    source: str
    token_id: str | None = None

    def has_scope(self, scope: str) -> bool:
        """Return whether the caller may use ``scope``."""
        if self.source == "jwt":
            return True
        return scope in self.scopes


def _token_live(token: ApiToken) -> bool:
    """Return whether ``token`` has not yet expired."""
    if token.expires_at is None:
        return True
    return as_utc(token.expires_at) > utcnow()


async def _from_jwt(session: AsyncSession, cred: str) -> Principal | None:
    """Build a principal from a user access JWT, or ``None``."""
    try:
        payload = decode_token(cred)
    except PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    user = await session.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        return None
    return Principal(user=user, scopes=ALL_SCOPES, source="jwt")


async def _from_token(session: AsyncSession, cred: str) -> Principal | None:
    """Build a principal from an API token, or ``None``."""
    result = await session.execute(
        select(ApiToken).where(ApiToken.token_hash == hash_token(cred))
    )
    token = result.scalar_one_or_none()
    if token is None or token.revoked or not _token_live(token):
        return None
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        return None
    token.last_used_at = utcnow()
    return Principal(
        user=user,
        scopes=frozenset(token.scopes),
        source="token",
        token_id=token.id,
    )


async def get_current_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    """Resolve the caller from a bearer JWT or an API token."""
    if creds is None:
        raise AuthError("Missing bearer token")
    principal = await _from_jwt(session, creds.credentials)
    if principal is None:
        principal = await _from_token(session, creds.credentials)
    if principal is None:
        raise AuthError("Invalid credentials")
    return principal


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


async def get_user_principal(principal: PrincipalDep) -> Principal:
    """Require an interactive user session (not an API token)."""
    if principal.source != "jwt":
        raise ForbiddenError("User session required")
    return principal


UserDep = Annotated[Principal, Depends(get_user_principal)]

ScopeDep = Callable[[Principal], Awaitable[Principal]]


def require_scope(scope: str) -> ScopeDep:
    """Return a dependency that enforces ``scope`` on the caller."""

    async def _dep(principal: PrincipalDep) -> Principal:
        if not principal.has_scope(scope):
            raise ForbiddenError(f"Missing scope: {scope}")
        return principal

    return _dep
