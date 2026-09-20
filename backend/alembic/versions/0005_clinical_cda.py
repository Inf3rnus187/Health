"""Add clinical (CDA) tables: observations and the stored document.

Owns its own tables, built from the ORM metadata (ADR-0004);
``create_all`` is checkfirst, so a fresh baseline is left untouched.

Revision ID: 0005_clinical_cda
Revises: 0004_raw_health_data
Create Date: 2026-09-20 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0005_clinical_cda"
down_revision: str | None = "0004_raw_health_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["clinical_observations", "clinical_documents"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the clinical tables from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the clinical tables."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
