"""Initial fixed schema.

Created directly from the ORM metadata so the migration is always
identical to the models — including PostgreSQL ``JSONB`` columns and the
dialect-specific partial unique indexes that enforce idempotency
(§5.2, §7.3). To stay reproducible as the schema grows, this migration
freezes the exact set of tables it owns; later migrations name their own
tables (see ADR-0004). The *dynamic* part (metrics + measurements) never
requires a migration.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASELINE_TABLES = [
    "users",
    "api_tokens",
    "auth_sessions",
    "metric_definitions",
    "events",
    "measurements",
    "photos",
    "photo_analyses",
    "automations",
    "reports",
    "audit_log",
]


def _tables() -> list:
    """Return the Table objects this migration owns."""
    return [Base.metadata.tables[name] for name in BASELINE_TABLES]


def upgrade() -> None:
    """Create the baseline tables from the ORM metadata."""
    Base.metadata.create_all(bind=op.get_bind(), tables=_tables())


def downgrade() -> None:
    """Drop the baseline tables."""
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tables())
