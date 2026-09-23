"""The files of evidence items: written encrypted, fingerprinted, read.

Each file keeps its SHA-256 as received, printed in the report, so a copy
can be checked against the original.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core import crypto
from app.core.config import get_settings
from app.models.work import Evidence


def attach(row: Evidence, upload: tuple[str, str, bytes]) -> None:
    """Write an item's file (encrypted at rest) and fingerprint it."""
    name, media, data = upload
    path = Path(get_settings().media_dir) / row.user_id / "evidence" / row.id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(crypto.encrypt(data))
    row.file_path, row.file_name, row.media_type = str(path), name, media
    row.size_bytes = len(data)
    row.sha256 = hashlib.sha256(data).hexdigest()


def read_file(row: Evidence) -> bytes | None:
    """The item's file, decrypted (None without a file)."""
    if not row.file_path:
        return None
    return crypto.decrypt(Path(row.file_path).read_bytes())
