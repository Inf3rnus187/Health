"""The count triggers read again only the bound a delete removed.

A sync of the iPhone app replaces its latest hourly sums: the delete
removes the last date of the ``healthkit`` group, and the trigger read
both dates again. The first one, through an index without the source,
came only after every older sample of the other sources: 160–180 ms per
type of sum on 930 000 samples, at every sync (1.2–3.5 s a sync at the
user's). Now only the removed bound is read again (``coalesce``): a few
ms. Same counts and dates. Guarded (ADR-0004): ``CREATE OR REPLACE`` and
``DROP TRIGGER IF EXISTS`` make it safe to run again.

Revision ID: 0029_sample_counts_one_bound
Revises: 0028_user_reconciled_commit
Create Date: 2026-10-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.models import sample_counts as model

revision: str = "0029_sample_counts_one_bound"
down_revision: str | None = "0028_user_reconciled_commit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The bounds as 0027 read them again (both, whichever was removed).
_BOTH = """        UPDATE sample_counts c SET
            first_at = (SELECT min(s.start_at) FROM health_samples s
                        WHERE s.user_id = c.user_id
                          AND s.metric_id = c.metric_id
                          AND s.source = c.source),
            last_at = (SELECT max(s.start_at) FROM health_samples s
                       WHERE s.user_id = c.user_id
                         AND s.metric_id = c.metric_id
                         AND s.source = c.source)
        WHERE c.first_at IS NULL OR c.last_at IS NULL;"""
#: The same, reading again only the removed one (as the model now does).
_ONE = """        UPDATE sample_counts c SET
            first_at = coalesce(c.first_at,
                (SELECT min(s.start_at) FROM health_samples s
                 WHERE s.user_id = c.user_id AND s.metric_id = c.metric_id
                   AND s.source = c.source)),
            last_at = coalesce(c.last_at,
                (SELECT max(s.start_at) FROM health_samples s
                 WHERE s.user_id = c.user_id AND s.metric_id = c.metric_id
                   AND s.source = c.source))
        WHERE c.first_at IS NULL OR c.last_at IS NULL;"""


def _postgresql() -> bool:
    """Whether the database is PostgreSQL (SQLite: tests only)."""
    return bool(op.get_bind().dialect.name == "postgresql")


def upgrade() -> None:
    """The trigger function (PostgreSQL) or the delete triggers (SQLite)."""
    if _postgresql():
        op.execute(model.postgresql()[1])  # CREATE OR REPLACE FUNCTION
        return
    _sqlite_triggers()


def downgrade() -> None:
    """Read both bounds again, as 0027 did."""
    if _postgresql():
        op.execute(model.postgresql()[1].replace(_ONE, _BOTH))
        return
    _sqlite_triggers()


def _sqlite_triggers() -> None:
    """The delete and update triggers of the model, made again."""
    op.execute("DROP TRIGGER IF EXISTS sample_counts_del")
    op.execute("DROP TRIGGER IF EXISTS sample_counts_upd")
    for statement in model.sqlite()[2:]:
        op.execute(statement)
