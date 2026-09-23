"""Absences: half days (from the afternoon, until noon).

Guarded like 0008 (ADR-0004): a fresh database built from live ORM
metadata already has the columns.

Revision ID: 0016_absence_halves
Revises: 0015_work_place
Create Date: 2026-09-23 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_absence_halves"
down_revision: str | None = "0015_work_place"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Column → default (whole days for every existing absence).
_COLUMNS = {"start_half": "am", "end_half": "pm"}


def _columns() -> set[str]:
    """The absences table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("absences")}


def upgrade() -> None:
    """Add start_half and end_half."""
    present = _columns()
    for name, default in _COLUMNS.items():
        if name not in present:
            op.add_column(
                "absences",
                sa.Column(
                    name,
                    sa.String(length=2),
                    nullable=False,
                    server_default=default,
                ),
            )


def downgrade() -> None:
    """Drop start_half and end_half."""
    present = _columns()
    for name in _COLUMNS:
        if name in present:
            op.drop_column("absences", name)
