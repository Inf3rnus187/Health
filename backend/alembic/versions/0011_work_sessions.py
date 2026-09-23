"""Add the work sessions table (clock-in / clock-out).

Owns its table, built from the ORM metadata (ADR-0004); ``create_all`` is
checkfirst, so a fresh baseline is left untouched.

Revision ID: 0011_work_sessions
Revises: 0010_meals
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0011_work_sessions"
down_revision: str | None = "0010_meals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["work_sessions"]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the work_sessions table from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the work_sessions table."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
