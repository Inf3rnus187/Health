"""Add full-fidelity Apple Health tables (raw import).

Owns its own set of tables and builds them from the ORM metadata, so
JSONB/index rendering stays correct per dialect and the migration is
reproducible (ADR-0004). ``create_all`` is checkfirst, so a fresh
database whose baseline already built these tables is left untouched.

Revision ID: 0004_raw_health_data
Revises: 0003_user_mfa
Create Date: 2026-09-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0004_raw_health_data"
down_revision: str | None = "0003_user_mfa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "health_samples",
    "workouts",
    "ecg_records",
    "route_files",
    "import_jobs",
]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in TABLES]


def upgrade() -> None:
    """Create the raw Apple Health tables from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the raw Apple Health tables."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
