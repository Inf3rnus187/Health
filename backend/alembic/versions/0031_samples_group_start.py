"""The samples indexed by count group: account, metric, source, date.

A delete that removes a group's first or last sample makes the count
trigger read the new bound (``min``/``max`` of ``start_at`` for that
account, metric and source). The only index by date had no source: the
bound of the app's samples (``healthkit``) came only after every sample
of the native export of the same metric — measured on fake data, 370 000
heart-rate samples: 666 ms for the newest, 10.7 s for the oldest, at
each sync deleting one (a sample removed in Health, a UUID sent again).
With this index: 5.7 ms and 2.2 ms. Built once (≈ 10 s for 2.4 million
samples; writes wait meanwhile). Guarded (ADR-0004): ``IF NOT EXISTS``.

Revision ID: 0031_samples_group_start
Revises: 0030_samples_stats_end
Create Date: 2026-10-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_samples_group_start"
down_revision: str | None = "0030_samples_stats_end"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The index of the samples by count group and date."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_samples_group_start ON health_samples "
        "(user_id, metric_id, source, start_at)"
    )


def downgrade() -> None:
    """Drop it."""
    op.execute("DROP INDEX IF EXISTS ix_samples_group_start")
