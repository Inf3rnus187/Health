"""A meal's reading may be put off: when it starts.

``meals.analysis_after`` (nullable): POST /meals ``analysis_delay_min``
puts the AI reading off; photos and changes sent meanwhile are read with
it. Guarded like 0025 (ADR-0004): a fresh database already has it.

Revision ID: 0026_meal_analysis_after
Revises: 0025_samples_user_start
Create Date: 2026-09-30 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_meal_analysis_after"
down_revision: str | None = "0025_samples_user_start"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "meals"
_COLUMN = "analysis_after"


def _columns() -> set[str]:
    """The table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    """Add the column where missing."""
    if _COLUMN not in _columns():
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Drop the column."""
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
