"""Raw samples by user and time, newest first without a sort.

``ix_samples_user_start`` on ``health_samples (user_id, start_at)``:
« Tout ce qui est enregistré » (Données) lists every metric by date;
without it PostgreSQL sorted millions of rows for each page (359 ms →
0.3 ms on 2.35 million samples, docs/performance.md). Guarded like
0024 (ADR-0004): a fresh database already has it.

Revision ID: 0025_samples_user_start
Revises: 0024_healthkit_ids
Create Date: 2026-09-30 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_samples_user_start"
down_revision: str | None = "0024_healthkit_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "health_samples"
_INDEX = "ix_samples_user_start"


def _indexes() -> set[str]:
    """The table's index names."""
    inspector = sa.inspect(op.get_bind())
    return {str(i["name"]) for i in inspector.get_indexes(_TABLE)}


def upgrade() -> None:
    """Add the index where missing."""
    if _INDEX not in _indexes():
        op.create_index(_INDEX, _TABLE, ["user_id", "start_at"])


def downgrade() -> None:
    """Drop the index."""
    if _INDEX in _indexes():
        op.drop_index(_INDEX, table_name=_TABLE)
