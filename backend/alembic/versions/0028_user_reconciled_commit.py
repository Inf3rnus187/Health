"""The hub's version of each user's last full reconcile.

``users.reconciled_commit`` (nullable): after an update of the hub (a
new GIT_COMMIT), the worker reconciles once each user whose last
reconcile ran on another version (services/reconcile_update.py).
Guarded like 0026 (ADR-0004): a fresh database already has it.

Revision ID: 0028_user_reconciled_commit
Revises: 0027_sample_counts
Create Date: 2026-09-30 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_user_reconciled_commit"
down_revision: str | None = "0027_sample_counts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "users"
_COLUMN = "reconciled_commit"


def _columns() -> set[str]:
    """The table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {str(c["name"]) for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    """Add the column where missing."""
    if _COLUMN not in _columns():
        op.add_column(
            _TABLE, sa.Column(_COLUMN, sa.String(40), nullable=True)
        )


def downgrade() -> None:
    """Drop the column."""
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
