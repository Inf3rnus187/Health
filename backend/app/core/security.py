"""Password hashing and opaque API-token hashing helpers.

User passwords use argon2id. API tokens are high-entropy random secrets,
so a fast SHA-256 digest (compared in constant time) is enough and lets
us index and look them up by digest without storing the secret.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2id hash of ``password``."""
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Return ``True`` when ``password`` matches ``hashed``."""
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def generate_token() -> str:
    """Return a fresh high-entropy opaque API token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the SHA-256 digest under which a token is stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(left: str, right: str) -> bool:
    """Compare two digests in constant time."""
    return hmac.compare_digest(left, right)
