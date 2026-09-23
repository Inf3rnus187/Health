"""Evidence: proofs and traces, their files encrypted at rest.

Proofs are calls, mails, screenshots…; traces are what third parties saw
(transport pass, taxi, parking, delivered meals, hotels, expense
reports). Each file keeps its SHA-256 as received, printed in the
report, so a copy can be checked against the original.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.base import new_uuid
from app.models.work import Evidence

#: Proof kind → French label.
PROOFS = {
    "appel": "Appel",
    "sms": "SMS / message",
    "mail": "Mail",
    "capture": "Capture d'écran",
    "note": "Note",
    "document": "Document",
    "autre": "Autre",
}
#: Trace kind → French label (a third party saw you, at a time).
TRACES = {
    "transport": "Transport (métro, Navigo, train)",
    "taxi": "Taxi / VTC",
    "parking": "Parking",
    "livraison": "Repas livré",
    "repas": "Repas acheté",
    "hotel": "Hôtel",
    "frais": "Note de frais",
}
#: Every kind → French label.
KINDS = {**PROOFS, **TRACES}


async def create(
    session: AsyncSession,
    user_id: str,
    fields: dict[str, Any],
    upload: tuple[str, str, bytes] | None,
) -> Evidence:
    """Store an item; ``upload`` is (file name, media type, bytes)."""
    row = Evidence(id=new_uuid(), user_id=user_id, **fields)
    if upload is not None:
        name, media, data = upload
        path = _path(user_id, row.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(crypto.encrypt(data))
        row.file_path, row.file_name, row.media_type = str(path), name, media
        row.size_bytes = len(data)
        row.sha256 = hashlib.sha256(data).hexdigest()
    session.add(row)
    await session.flush()
    return row


async def list_items(
    session: AsyncSession,
    user_id: str,
    first: date | None = None,
    last: date | None = None,
) -> list[Evidence]:
    """Items between two days (all by default), oldest first."""
    query = select(Evidence).where(Evidence.user_id == user_id)
    if first is not None:
        query = query.where(
            Evidence.occurred_at
            >= datetime.combine(first, time.min, tzinfo=UTC)
        )
    if last is not None:
        end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=UTC)
        query = query.where(Evidence.occurred_at < end)
    rows = await session.execute(query.order_by(Evidence.occurred_at))
    return list(rows.scalars())


async def get(session: AsyncSession, user_id: str, item_id: str) -> Evidence:
    """One of the user's items or NotFoundError."""
    row = await session.get(Evidence, item_id)
    if row is None or row.user_id != user_id:
        raise NotFoundError("Evidence not found")
    return row


async def delete(session: AsyncSession, user_id: str, item_id: str) -> None:
    """Delete an item and its file."""
    row = await get(session, user_id, item_id)
    if row.file_path:
        Path(row.file_path).unlink(missing_ok=True)
    await session.delete(row)
    await session.flush()


def read_file(row: Evidence) -> bytes | None:
    """The item's file, decrypted (None without a file)."""
    if not row.file_path:
        return None
    return crypto.decrypt(Path(row.file_path).read_bytes())


def _path(user_id: str, item_id: str) -> Path:
    """On-disk location of an item's file."""
    return Path(get_settings().media_dir) / user_id / "evidence" / item_id
