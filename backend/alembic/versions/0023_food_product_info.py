"""Foods: Open Food Facts' details (ingredients, Nutri-Score, NOVA…).

Guarded like 0021 (ADR-0004). Existing sheets have none until their
barcode is looked up again (« Chercher » in the sheet's Code-barres).

Revision ID: 0023_food_product_info
Revises: 0022_food_stock
Create Date: 2026-09-25 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.base import JSONColumn

revision: str = "0023_food_product_info"
down_revision: str | None = "0022_food_stock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _present() -> bool:
    """Whether the foods table already has the column."""
    inspector = sa.inspect(op.get_bind())
    return any(
        c["name"] == "product_info" for c in inspector.get_columns("foods")
    )


def upgrade() -> None:
    """Add product_info."""
    if not _present():
        op.add_column(
            "foods", sa.Column("product_info", JSONColumn, nullable=True)
        )


def downgrade() -> None:
    """Drop product_info."""
    if _present():
        op.drop_column("foods", "product_info")
