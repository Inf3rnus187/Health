"""Food stock: purchases, losses and counts of « Mes aliments ».

The table is created from the ORM metadata (ADR-0004), guarded: a fresh
database already has it. Nothing is filled: a food has a stock once a
purchase or a count is entered; what was eaten is read from the meals.

Revision ID: 0022_food_stock
Revises: 0021_food_portion
Create Date: 2026-09-25 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0022_food_stock"
down_revision: str | None = "0021_food_portion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "food_stock_moves"


def upgrade() -> None:
    """Create food_stock_moves (if missing)."""
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[_TABLE]]
    )


def downgrade() -> None:
    """Drop food_stock_moves."""
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables[_TABLE]]
    )
