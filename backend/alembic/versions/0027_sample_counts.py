"""Raw samples counted per metric and source, kept exact by triggers.

``sample_counts (user_id, metric_id, source, n, first_at, last_at)``
and the ``health_samples`` triggers that keep it exact at each insert,
update, delete and truncate (app/models/sample_counts.py). The inventory
(Données) reads it: 0.29 s → a few ms on 2.4 million samples
(docs/performance.md). Filled from the samples here, the table locked
against writes meanwhile. Guarded (ADR-0004): a fresh database already
has it (created with ``health_samples``); ``CREATE … IF NOT EXISTS``,
``CREATE OR REPLACE`` and ``DROP TRIGGER IF EXISTS`` make it safe to run
again.

Revision ID: 0027_sample_counts
Revises: 0026_meal_analysis_after
Create Date: 2026-09-30 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.models import sample_counts as model

revision: str = "0027_sample_counts"
down_revision: str | None = "0026_meal_analysis_after"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _postgresql() -> bool:
    """Whether the database is PostgreSQL (SQLite: tests only)."""
    return bool(op.get_bind().dialect.name == "postgresql")


def upgrade() -> None:
    """The table, its triggers, and the counts of the samples there."""
    pg = _postgresql()
    if pg:
        op.execute("LOCK TABLE health_samples IN SHARE MODE")
    for statement in model.postgresql() if pg else model.sqlite():
        op.execute(statement)
    op.execute("DELETE FROM sample_counts")
    op.execute(model.REFILL.format(where=""))


def downgrade() -> None:
    """Drop the triggers, their functions and the table."""
    for name in ("ins", "upd", "del", "trunc"):
        op.execute(
            f"DROP TRIGGER IF EXISTS sample_counts_{name}"
            + (" ON health_samples" if _postgresql() else "")
        )
    if _postgresql():
        op.execute("DROP FUNCTION IF EXISTS sample_counts_sync()")
        op.execute("DROP FUNCTION IF EXISTS sample_counts_clear()")
    op.execute("DROP TABLE IF EXISTS sample_counts")
