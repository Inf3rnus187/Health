"""Add the meal journal table.

Owns its table, built from the ORM metadata (ADR-0004); ``create_all`` is
checkfirst, so a fresh baseline is left untouched.

Revision ID: 0010_meals
Revises: 0009_report_summary
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0010_meals"
down_revision: str | None = "0009_report_summary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["meals"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the meals table from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the meals table."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
