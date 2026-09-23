"""Work sessions: where the work was done (on site or remote).

Guarded like 0008 (ADR-0004): a fresh database built from live ORM
metadata already has the column.

Revision ID: 0015_work_place
Revises: 0014_trace_time_known
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_work_place"
down_revision: str | None = "0014_trace_time_known"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    """The work sessions table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("work_sessions")}


def upgrade() -> None:
    """Add place ("site" for every existing session)."""
    if "place" not in _columns():
        op.add_column(
            "work_sessions",
            sa.Column(
                "place",
                sa.String(length=12),
                nullable=False,
                server_default="site",
            ),
        )


def downgrade() -> None:
    """Drop place."""
    if "place" in _columns():
        op.drop_column("work_sessions", "place")
