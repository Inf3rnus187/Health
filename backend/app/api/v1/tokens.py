"""Scoped API-token management (interactive users only)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import InteractiveDep, SessionDep
from app.models.token import ApiToken
from app.schemas.common import Message
from app.schemas.token import TokenCreate, TokenCreated, TokenOut
from app.services import audit
from app.services import tokens as svc

router = APIRouter(prefix="/tokens", tags=["tokens"])


@router.post(
    "", response_model=TokenCreated, status_code=status.HTTP_201_CREATED
)
async def create(
    body: TokenCreate, principal: InteractiveDep, session: SessionDep
) -> TokenCreated:
    """Mint a scoped token; the secret is returned only once."""
    token, secret = await svc.create_token(
        session, principal.user, body.name, body.scopes, body.expires_at
    )
    await audit.record(
        session,
        action="create",
        entity="api_token",
        user_id=principal.user.id,
        entity_id=token.id,
    )
    await session.commit()
    data = TokenOut.model_validate(token).model_dump()
    return TokenCreated(**data, token=secret)


@router.get("", response_model=list[TokenOut])
async def index(
    principal: InteractiveDep, session: SessionDep
) -> list[ApiToken]:
    """List the caller's API tokens (secrets are never returned)."""
    return await svc.list_tokens(session, principal.user)


@router.delete("/{token_id}", response_model=Message)
async def delete(
    token_id: str, principal: InteractiveDep, session: SessionDep
) -> Message:
    """Revoke one of the caller's API tokens."""
    await svc.revoke_token(session, principal.user, token_id)
    await audit.record(
        session,
        action="revoke",
        entity="api_token",
        user_id=principal.user.id,
        entity_id=token_id,
    )
    await session.commit()
    return Message(detail="revoked")
