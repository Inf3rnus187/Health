"""Foods: the portion usually eaten (the small box, ¼ of the big one).

Guarded like 0018 (ADR-0004): a fresh database built from live ORM
metadata already has the column. Existing foods have none: a meal
naming them without a quantity is read as before.

Revision ID: 0021_food_portion
Revises: 0020_report_hash
Create Date: 2026-09-25 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_food_portion"
down_revision: str | None = "0020_report_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _present() -> bool:
    """Whether the foods table already has the column."""
    inspector = sa.inspect(op.get_bind())
    return any(c["name"] == "portion_g" for c in inspector.get_columns("foods"))


def upgrade() -> None:
    """Add portion_g."""
    if not _present():
        op.add_column(
            "foods", sa.Column("portion_g", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    """Drop portion_g."""
    if _present():
        op.drop_column("foods", "portion_g")
