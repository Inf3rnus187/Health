"""Initial fixed schema.

The baseline is created directly from the ORM metadata so that the
migration is always identical to the models — including PostgreSQL
``JSONB`` columns and the dialect-specific partial unique indexes that
enforce idempotency (§5.2, §7.3). The *dynamic* part of the system
(metric definitions and their measurements) never requires a migration.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create every fixed table from the ORM metadata."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop every fixed table."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
