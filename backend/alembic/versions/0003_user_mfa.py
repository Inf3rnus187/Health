"""Add optional MFA (TOTP) columns to users (Phase 9, §12.1).

Idempotent: because the ``0001`` baseline builds tables from live ORM
metadata, a fresh database already has these columns, while a database
created before this revision does not. Guarding on column existence makes
the migration correct on both (ADR-0004).

Revision ID: 0003_user_mfa
Revises: 0002_ingest_mappings
Create Date: 2026-03-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_user_mfa"
down_revision: str | None = "0002_ingest_mappings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    """Return the existing column names of ``table``."""
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    """Add mfa_secret and mfa_enabled to users if absent."""
    existing = _columns("users")
    if "mfa_secret" not in existing:
        op.add_column(
            "users",
            sa.Column("mfa_secret", sa.String(length=64), nullable=True),
        )
    if "mfa_enabled" not in existing:
        op.add_column(
            "users",
            sa.Column(
                "mfa_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    """Drop the MFA columns if present."""
    existing = _columns("users")
    if "mfa_enabled" in existing:
        op.drop_column("users", "mfa_enabled")
    if "mfa_secret" in existing:
        op.drop_column("users", "mfa_secret")
