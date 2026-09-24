"""Reports: the SHA-256 of the file, to check a copy is authentic.

Guarded like 0008 (ADR-0004). Reports made before keep no hash.

Revision ID: 0020_report_hash
Revises: 0019_medication_intakes
Create Date: 2026-09-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_report_hash"
down_revision: str | None = "0019_medication_intakes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    """The reports table's column names."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("reports")}


def upgrade() -> None:
    """Add reports.sha256."""
    if "sha256" not in _columns():
        op.add_column(
            "reports", sa.Column("sha256", sa.String(64), nullable=True)
        )


def downgrade() -> None:
    """Drop reports.sha256."""
    if "sha256" in _columns():
        op.drop_column("reports", "sha256")
