"""Background jobs for documents and data consistency (ARQ)."""

from __future__ import annotations

from typing import Any


async def analyze_document(ctx: dict[str, Any], doc_id: str) -> str:
    """Read a medical document into grounded values (document model)."""
    from app.core.db import SessionFactory
    from app.services import document_ai

    async with SessionFactory() as session:
        await document_ai.run(session, doc_id)
    return doc_id


async def reconcile_data(ctx: dict[str, Any], user_id: str) -> str:
    """Merge duplicate keys and rebuild daily values from raw samples."""
    from app.core.db import SessionFactory
    from app.services import reconcile

    async with SessionFactory() as session:
        await reconcile.run(session, user_id)
    return user_id
