"""Optional at-rest encryption for stored media (§12).

When ``MEDIA_ENCRYPTION_KEY`` (a Fernet key) is set, media bytes are
encrypted on write and decrypted on read; otherwise the functions are a
transparent passthrough. Generate a key with::

    python -c "from cryptography.fernet import Fernet; \
        print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

from cryptography.fernet import Fernet

from app.core.config import get_settings

_key = get_settings().media_encryption_key
_fernet = Fernet(_key.encode()) if _key else None


def enabled() -> bool:
    """Return whether at-rest media encryption is active."""
    return _fernet is not None


def encrypt(data: bytes) -> bytes:
    """Encrypt ``data`` when a key is configured, else return it as-is."""
    return _fernet.encrypt(data) if _fernet else data


def decrypt(data: bytes) -> bytes:
    """Decrypt ``data`` when a key is configured, else return it as-is."""
    return _fernet.decrypt(data) if _fernet else data
