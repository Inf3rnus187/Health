"""Add the ingest_mappings table (Phase 3, §7.1).

An incremental migration from the baseline: it creates only its own
table from the ORM metadata, so JSONB/index rendering stays correct per
dialect and the migration is reproducible (ADR-0004).

Revision ID: 0002_ingest_mappings
Revises: 0001_initial
Create Date: 2026-02-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0002_ingest_mappings"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["ingest_mappings"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the ingest_mappings table from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the ingest_mappings table."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
