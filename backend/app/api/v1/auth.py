"""Authentication endpoints: login, refresh, logout and profile."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import PrincipalDep, SessionDep
from app.core.scopes import HUB_FULL
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from app.schemas.common import Message
from app.services import audit
from app.services import auth as svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: SessionDep) -> TokenPair:
    """Authenticate and return an access+refresh token pair."""
    user = await svc.authenticate(session, body.email, body.password, body.otp)
    pair = await svc.login(session, user)
    await audit.record(session, action="login", entity="user", user_id=user.id)
    await session.commit()
    return pair


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenPair:
    """Rotate a refresh token and return a new pair."""
    pair = await svc.refresh(session, body.refresh_token)
    await session.commit()
    return pair


@router.post("/logout", response_model=Message)
async def logout(body: RefreshRequest, session: SessionDep) -> Message:
    """Revoke the session behind the given refresh token."""
    await svc.logout(session, body.refresh_token)
    await session.commit()
    return Message(detail="logged out")


@router.get("/me", response_model=UserOut)
async def me(principal: PrincipalDep) -> User:
    """Return the currently authenticated user."""
    return principal.user


@router.get("/scopes")
async def scopes(principal: PrincipalDep) -> dict[str, object]:
    """How the caller is authenticated and what it may do (MCP gate)."""
    full = principal.source == "jwt" or principal.has_scope(HUB_FULL)
    return {
        "source": principal.source,
        "scopes": sorted(principal.scopes),
        "full_access": full,
    }
