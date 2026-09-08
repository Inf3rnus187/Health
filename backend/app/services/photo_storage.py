"""Filesystem layout for photos, kept outside the web root (§12).

Media lives under ``MEDIA_DIR/<user_id>/`` and is only ever served by an
authenticated endpoint — never by the static web tier.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings

_settings = get_settings()


def user_dir(user_id: str) -> Path:
    """Return (creating if needed) the media directory for a user."""
    base = Path(_settings.media_dir) / user_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_original(
    user_id: str, photo_id: str, angle: str, ext: str, data: bytes
) -> Path:
    """Persist the uploaded bytes and return the stored path."""
    path = user_dir(user_id) / f"{photo_id}_orig_{angle}{ext}"
    path.write_bytes(data)
    return path


def normalized_path(user_id: str, photo_id: str, angle: str) -> Path:
    """Return the path the normalized JPEG will be written to."""
    return user_dir(user_id) / f"{photo_id}_norm_{angle}.jpg"
