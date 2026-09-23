"""Work file: incomplete sessions, absences, evidence.

A session may now miss its clock-in (a departure logged alone), so
``work_sessions.start_at`` becomes nullable. The absences (sick leave…)
and evidence (calls, mails, screenshots) tables are created from the ORM
metadata (ADR-0004); both steps are guarded, so a fresh baseline built
from live metadata is left untouched.

Revision ID: 0012_work_file
Revises: 0011_work_sessions
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision: str = "0012_work_file"
down_revision: str | None = "0011_work_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["absences", "evidence"]


def _start_nullable() -> bool:
    """Whether work_sessions.start_at already accepts NULL."""
    columns = sa.inspect(op.get_bind()).get_columns("work_sessions")
    return any(c["name"] == "start_at" and c["nullable"] for c in columns)


def upgrade() -> None:
    """Relax start_at, create the absences and evidence tables."""
    if not _start_nullable():
        with op.batch_alter_table("work_sessions") as batch:
            batch.alter_column(
                "start_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=True,
            )
    tables = [Base.metadata.tables[name] for name in TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    """Drop the new tables (start_at stays nullable)."""
    tables = [Base.metadata.tables[name] for name in reversed(TABLES)]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)
