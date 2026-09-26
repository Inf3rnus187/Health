"""Raw samples and workouts keep their HealthKit UUID (iPhone app sync).

``external_id`` on ``health_samples`` and ``workouts``, unique per user
(NULL for everything imported before: files carry no UUID). Guarded
like 0023 (ADR-0004): a fresh database already has them.

Revision ID: 0024_healthkit_ids
Revises: 0023_food_product_info
Create Date: 2026-09-26 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_healthkit_ids"
down_revision: str | None = "0023_food_product_info"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: table → its unique (user_id, external_id) index.
_TABLES = {
    "health_samples": "ux_samples_user_external",
    "workouts": "ux_workouts_user_external",
}


def _columns(table: str) -> set[str]:
    """The table's column names."""
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    """The table's index names."""
    inspector = sa.inspect(op.get_bind())
    return {str(i["name"]) for i in inspector.get_indexes(table)}


def upgrade() -> None:
    """Add external_id and its unique index where missing."""
    for table, index in _TABLES.items():
        if "external_id" not in _columns(table):
            op.add_column(
                table,
                sa.Column("external_id", sa.String(64), nullable=True),
            )
        if index not in _indexes(table):
            op.create_index(
                index, table, ["user_id", "external_id"], unique=True
            )


def downgrade() -> None:
    """Drop the index and the column."""
    for table, index in _TABLES.items():
        if index in _indexes(table):
            op.drop_index(index, table_name=table)
        if "external_id" in _columns(table):
            op.drop_column(table, "external_id")
