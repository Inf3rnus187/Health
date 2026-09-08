"""Filesystem layout for photos, kept outside the web root (§12).

Media lives under ``MEDIA_DIR/<user_id>/`` and is only ever served by an
authenticated endpoint. All reads/writes go through the crypto layer, so
files are transparently encrypted at rest when a key is configured.
"""

from __future__ import annotations

from pathlib import Path

from app.core import crypto
from app.core.config import get_settings

_settings = get_settings()


def user_dir(user_id: str) -> Path:
    """Return (creating if needed) the media directory for a user."""
    base = Path(_settings.media_dir) / user_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def original_path(user_id: str, photo_id: str, angle: str, ext: str) -> Path:
    """Return the path for a photo's stored original."""
    return user_dir(user_id) / f"{photo_id}_orig_{angle}{ext}"


def normalized_path(user_id: str, photo_id: str, angle: str) -> Path:
    """Return the path for a photo's normalized JPEG."""
    return user_dir(user_id) / f"{photo_id}_norm_{angle}.jpg"


def write_bytes(path: Path, data: bytes) -> None:
    """Encrypt (if configured) and write ``data`` to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(crypto.encrypt(data))


def read_bytes(path: Path) -> bytes:
    """Read and decrypt (if configured) the bytes at ``path``."""
    return crypto.decrypt(path.read_bytes())
