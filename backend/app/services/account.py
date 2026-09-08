"""Account erasure — RGPD right to be forgotten (§12).

Deleting the user cascades to all their data (measurements, events,
photos, tokens, sessions, automations, mappings) via ON DELETE CASCADE;
their media and export files are removed from disk too.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User

_settings = get_settings()


def _purge_files(user_id: str) -> None:
    """Remove a user's media and export directories."""
    for base in (_settings.media_dir, _settings.exports_dir):
        shutil.rmtree(Path(base) / user_id, ignore_errors=True)


async def erase(session: AsyncSession, user: User) -> None:
    """Delete a user's files and account (cascades all their data)."""
    _purge_files(user.id)
    await session.delete(user)
    await session.flush()
