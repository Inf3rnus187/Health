"""Add the AI clinical synthesis of a report (JSON).

Guarded like 0008 (ADR-0004): a fresh database built from live ORM
metadata already has the column.

Revision ID: 0009_report_summary
Revises: 0008_document_analysis
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0009_report_summary"
down_revision: str | None = "0008_document_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "reports"


def _columns() -> set[str]:
    """Return the existing column names of the reports table."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(TABLE)}


def upgrade() -> None:
    """Add summary if absent."""
    if "summary" not in _columns():
        json_type = sa.JSON().with_variant(JSONB(), "postgresql")
        op.add_column(TABLE, sa.Column("summary", json_type, nullable=True))


def downgrade() -> None:
    """Drop summary if present."""
    if "summary" in _columns():
        op.drop_column(TABLE, "summary")
