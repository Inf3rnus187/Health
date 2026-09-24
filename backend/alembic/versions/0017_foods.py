"""Foods catalogue; meals get more photos and their foods.

The foods table (a user's usual boxes and sachets, their label values)
is created from the ORM metadata (ADR-0004); meals gain ``photos`` (the
pack, the nutrition label…) and ``foods`` (the catalogue foods in it).
Guarded like 0008: a fresh database built from live metadata already
has them.

Revision ID: 0017_foods
Revises: 0016_absence_halves
Create Date: 2026-09-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models import Base
from app.models.base import JSONColumn

revision: str = "0017_foods"
down_revision: str | None = "0016_absence_halves"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEAL_COLUMNS = ("photos", "foods")


def _meal_columns() -> set[str]:
    """The meals table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("meals")}


def upgrade() -> None:
    """Create foods; add meals.photos and meals.foods (empty lists)."""
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[Base.metadata.tables["foods"]]
    )
    present = _meal_columns()
    for name in _MEAL_COLUMNS:
        if name not in present:
            op.add_column(
                "meals",
                sa.Column(
                    name, JSONColumn, nullable=False, server_default="[]"
                ),
            )


def downgrade() -> None:
    """Drop the meal columns and the foods table."""
    present = _meal_columns()
    for name in _MEAL_COLUMNS:
        if name in present:
            op.drop_column("meals", name)
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[Base.metadata.tables["foods"]]
    )
