"""Creation, listing and revocation of scoped API tokens."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.security import generate_token, hash_token
from app.models.token import ApiToken
from app.models.user import User


async def create_token(
    session: AsyncSession,
    user: User,
    name: str,
    scopes: list[str],
    expires_at: datetime | None,
) -> tuple[ApiToken, str]:
    """Mint a token, returning the row and one-time plaintext secret."""
    plaintext = generate_token()
    token = ApiToken(
        user_id=user.id,
        name=name,
        token_hash=hash_token(plaintext),
        scopes=scopes,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token, plaintext


async def list_tokens(session: AsyncSession, user: User) -> list[ApiToken]:
    """Return the user's tokens, newest first."""
    result = await session.execute(
        select(ApiToken)
        .where(ApiToken.user_id == user.id)
        .order_by(ApiToken.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_token(
    session: AsyncSession, user: User, token_id: str
) -> None:
    """Revoke one of the user's tokens."""
    token = await session.get(ApiToken, token_id)
    if token is None or token.user_id != user.id:
        raise NotFoundError("Token not found")
    token.revoked = True
