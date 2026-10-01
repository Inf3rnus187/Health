"""The iPhone app's sums indexed by their end (a partial index).

Each sync replaces the stored sums its own overlap (``start < high AND
end > low``). Without an index on the end, PostgreSQL read the metric's
whole history up to ``high``, native export included: ≈ 70 ms to find
and as much to delete, per type of sum and per sync. The partial index
holds only those sums (``external_id LIKE 'stat:%'``, a few hundred kB)
and finds them in a few rows. Guarded (ADR-0004): ``IF NOT EXISTS``.

Revision ID: 0030_samples_stats_end
Revises: 0029_sample_counts_one_bound
Create Date: 2026-10-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.models.health_raw import STATS_ONLY

revision: str = "0030_samples_stats_end"
down_revision: str | None = "0029_sample_counts_one_bound"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The partial index of the sums by their end."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_samples_stats_end ON health_samples "
        f"(user_id, metric_id, end_at) WHERE {STATS_ONLY}"
    )


def downgrade() -> None:
    """Drop it."""
    op.execute("DROP INDEX IF EXISTS ix_samples_stats_end")
