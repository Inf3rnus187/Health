"""Optional TOTP multi-factor authentication (§12.1)."""

from __future__ import annotations

import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AuthError
from app.models.user import User


def verify_code(user: User, code: str) -> bool:
    """Return whether ``code`` is valid for the user's TOTP secret."""
    if not user.mfa_secret:
        return False
    return pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1)


async def setup(session: AsyncSession, user: User) -> str:
    """Assign a fresh secret (not yet enabled) and return the otpauth URI."""
    user.mfa_secret = pyotp.random_base32()
    await session.flush()
    return pyotp.TOTP(user.mfa_secret).provisioning_uri(
        name=user.email, issuer_name=get_settings().mfa_issuer
    )


async def enable(session: AsyncSession, user: User, code: str) -> None:
    """Enable MFA after verifying a code from the authenticator."""
    if not verify_code(user, code):
        raise AuthError("Invalid MFA code")
    user.mfa_enabled = True
    await session.flush()


async def disable(session: AsyncSession, user: User, code: str) -> None:
    """Disable MFA and clear the secret after verifying a code."""
    if not verify_code(user, code):
        raise AuthError("Invalid MFA code")
    user.mfa_enabled = False
    user.mfa_secret = None
    await session.flush()
