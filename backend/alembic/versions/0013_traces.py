"""Traces and expenses: evidence end time, place, amount; meal price.

Evidence gains what a trace carries (parking exit, taxi drop-off, a
place, an amount, the meal a delivery was logged as); meals gain their
price and vendor. Guarded like 0008 (ADR-0004): a fresh database built
from live ORM metadata already has the columns.

Revision ID: 0013_traces
Revises: 0012_work_file
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_traces"
down_revision: str | None = "0012_work_file"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)
COLUMNS: dict[str, list[sa.Column]] = {
    "evidence": [
        sa.Column("ended_at", _TZ, nullable=True),
        sa.Column("place", sa.String(300), nullable=False, server_default=""),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column(
            "currency", sa.String(3), nullable=False, server_default="EUR"
        ),
        sa.Column(
            "meal_id",
            sa.String(36),
            sa.ForeignKey("meals.id", ondelete="SET NULL"),
            nullable=True,
        ),
    ],
    "meals": [
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("vendor", sa.String(120), nullable=False, server_default=""),
    ],
}


def _existing(table: str) -> set[str]:
    """The column names a table already has."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    """Add the missing columns."""
    for table, columns in COLUMNS.items():
        have = _existing(table)
        for column in columns:
            if column.name not in have:
                op.add_column(table, column)


def downgrade() -> None:
    """Drop the added columns."""
    for table, columns in COLUMNS.items():
        have = _existing(table)
        for column in columns:
            if column.name in have:
                op.drop_column(table, column.name)
