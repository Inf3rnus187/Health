"""Add the AI analysis of medical documents (status + JSON result).

Idempotent like 0003: ``0006`` builds ``medical_documents`` from live ORM
metadata, so a fresh database already has these columns (ADR-0004).

Revision ID: 0008_document_analysis
Revises: 0007_care
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008_document_analysis"
down_revision: str | None = "0007_care"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "medical_documents"


def _columns() -> set[str]:
    """Return the existing column names of the documents table."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(TABLE)}


def upgrade() -> None:
    """Add analysis_status and analysis if absent."""
    existing = _columns()
    if "analysis_status" not in existing:
        op.add_column(
            TABLE,
            sa.Column("analysis_status", sa.String(length=16), nullable=True),
        )
    if "analysis" not in existing:
        json_type = sa.JSON().with_variant(JSONB(), "postgresql")
        op.add_column(TABLE, sa.Column("analysis", json_type, nullable=True))


def downgrade() -> None:
    """Drop the analysis columns if present."""
    existing = _columns()
    for name in ("analysis", "analysis_status"):
        if name in existing:
            op.drop_column(TABLE, name)
