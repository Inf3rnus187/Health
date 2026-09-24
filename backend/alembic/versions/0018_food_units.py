"""Foods: a unit (« 1 tomate » = 120 g), the values' source, a barcode.

Guarded like 0008 (ADR-0004): a fresh database built from live ORM
metadata already has the columns. Existing foods keep their values;
their unit is empty and their source blank until edited.

Revision ID: 0018_food_units
Revises: 0017_foods
Create Date: 2026-09-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_food_units"
down_revision: str | None = "0017_foods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = {
    "unit_name": sa.String(40),
    "unit_g": sa.Float(),
    "source": sa.String(200),
    "barcode": sa.String(20),
}
_TEXT = {"unit_name", "source", "barcode"}


def _columns() -> set[str]:
    """The foods table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("foods")}


def upgrade() -> None:
    """Add unit_name, unit_g, source and barcode."""
    present = _columns()
    for name, kind in _COLUMNS.items():
        if name in present:
            continue
        text = name in _TEXT
        op.add_column(
            "foods",
            sa.Column(
                name,
                kind,
                nullable=not text,
                server_default="" if text else None,
            ),
        )


def downgrade() -> None:
    """Drop the four columns."""
    present = _columns()
    for name in _COLUMNS:
        if name in present:
            op.drop_column("foods", name)
