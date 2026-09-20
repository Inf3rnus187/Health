"""Add the medical_documents table.

Owns its own table, built from the ORM metadata (ADR-0004);
``create_all`` is checkfirst, so a fresh baseline is left untouched.

Revision ID: 0006_medical_documents
Revises: 0005_clinical_cda
Create Date: 2026-09-20 22:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0006_medical_documents"
down_revision: str | None = "0005_clinical_cda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["medical_documents"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the medical_documents table from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the medical_documents table."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
