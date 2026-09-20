"""Store and manage uploaded medical documents (encrypted at rest)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.medical import MedicalDocument

_settings = get_settings()


async def create_document(
    session: AsyncSession,
    user_id: str,
    *,
    meta: Mapping[str, Any],
    data: bytes,
) -> MedicalDocument:
    """Persist a document's metadata and write its encrypted file."""
    doc = MedicalDocument(
        user_id=user_id, file_path="", size_bytes=len(data), **meta
    )
    session.add(doc)
    await session.flush()
    path = _path(user_id, doc.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(crypto.encrypt(data))
    doc.file_path = str(path)
    await session.flush()
    return doc


async def list_documents(
    session: AsyncSession, user_id: str
) -> list[MedicalDocument]:
    """Return the user's documents, newest first."""
    result = await session.execute(
        select(MedicalDocument)
        .where(MedicalDocument.user_id == user_id)
        .order_by(MedicalDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(
    session: AsyncSession, user_id: str, doc_id: str
) -> MedicalDocument:
    """Return one of the user's documents or raise NotFound."""
    doc = await session.get(MedicalDocument, doc_id)
    if doc is None or doc.user_id != user_id:
        raise NotFoundError("Document not found")
    return doc


async def delete_document(
    session: AsyncSession, user_id: str, doc_id: str
) -> None:
    """Delete a document row and unlink its file."""
    doc = await get_document(session, user_id, doc_id)
    Path(doc.file_path).unlink(missing_ok=True)
    await session.delete(doc)
    await session.flush()


def read_file(doc: MedicalDocument) -> bytes:
    """Read and decrypt a document's stored bytes."""
    return crypto.decrypt(Path(doc.file_path).read_bytes())


def _path(user_id: str, doc_id: str) -> Path:
    """On-disk location for a stored document."""
    return Path(_settings.media_dir) / user_id / "medical" / doc_id
