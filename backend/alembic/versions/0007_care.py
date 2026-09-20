"""Add care tables: conditions, treatments, appointments.

Owns its own tables, built from the ORM metadata (ADR-0004);
``create_all`` is checkfirst, so a fresh baseline is left untouched.

Revision ID: 0007_care
Revises: 0006_medical_documents
Create Date: 2026-09-20 23:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0007_care"
down_revision: str | None = "0006_medical_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["conditions", "treatments", "appointments"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the care tables from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the care tables."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
