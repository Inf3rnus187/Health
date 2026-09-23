"""Evidence: whether the time of a trace is known (or only its day).

Guarded like 0008 (ADR-0004): a fresh database built from live ORM
metadata already has the column.

Revision ID: 0014_trace_time_known
Revises: 0013_traces
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_trace_time_known"
down_revision: str | None = "0013_traces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    """The evidence table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("evidence")}


def upgrade() -> None:
    """Add time_known (true for every existing item)."""
    if "time_known" not in _columns():
        op.add_column(
            "evidence",
            sa.Column(
                "time_known",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    """Drop time_known."""
    if "time_known" in _columns():
        op.drop_column("evidence", "time_known")
