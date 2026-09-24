"""Medication intakes (each dose, when, how entered); doses per day.

The table is created from the ORM metadata (ADR-0004); treatments gain
``doses_per_day`` (empty for existing ones: « as needed » until set).
Guarded like 0008.

Revision ID: 0019_medication_intakes
Revises: 0018_food_units
Create Date: 2026-09-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.models import Base

revision: str = "0019_medication_intakes"
down_revision: str | None = "0018_food_units"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _treatment_columns() -> set[str]:
    """The treatments table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("treatments")}


def upgrade() -> None:
    """Create medication_intakes; add treatments.doses_per_day."""
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables["medication_intakes"]],
    )
    if "doses_per_day" not in _treatment_columns():
        op.add_column(
            "treatments",
            sa.Column("doses_per_day", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    """Drop the column and the table."""
    if "doses_per_day" in _treatment_columns():
        op.drop_column("treatments", "doses_per_day")
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables["medication_intakes"]],
    )
