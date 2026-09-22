"""Scope check that also accepts a ``?token=`` query parameter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    Principal,
    SessionDep,
    _bearer,
    _from_jwt,
    _from_token,
)
from app.core.errors import AuthError, ForbiddenError


async def _resolve(
    session: AsyncSession,
    creds: HTTPAuthorizationCredentials | None,
    token: str | None,
) -> Principal | None:
    """Resolve a principal from a bearer header or a ``token`` query."""
    if creds is not None:
        principal = await _from_jwt(session, creds.credentials)
        return principal or await _from_token(session, creds.credentials)
    if token:
        return await _from_token(session, token)
    return None


def require_scope_flex(
    scope: str,
) -> Callable[..., Awaitable[Principal]]:
    """Like ``require_scope`` but also accepts a ``?token=`` query param.

    Lets an iPhone Shortcut authenticate an upload via the URL alone, with
    no ``Authorization`` header to hand-enter.
    """

    async def _dep(
        session: SessionDep,
        creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        token: Annotated[str | None, Query()] = None,
    ) -> Principal:
        principal = await _resolve(session, creds, token)
        if principal is None:
            raise AuthError("Invalid credentials")
        if not principal.has_scope(scope):
            raise ForbiddenError(f"Missing scope: {scope}")
        return principal

    return _dep
