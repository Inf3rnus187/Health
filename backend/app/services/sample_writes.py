"""Raw samples written in bulk: one ``COPY`` on PostgreSQL.

SQLAlchemy hands a list of rows to asyncpg one row at a time
(``executemany``): the trigger that keeps ``sample_counts`` exact, meant
to run once per statement, then ran once per row — half of the time of
writing a sample. PostgreSQL's ``COPY`` writes them in one statement,
the trigger running once: 0.19–0.22 s for 5 000 samples instead of
0.59–0.66 s (docs/performance.md). The same rows, the same checks (keys,
unique HealthKit ids), in the same transaction. SQLite (the tests) keeps
SQLAlchemy's insert.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_raw import HealthSample
from app.services.healthkit_common import chunks

_COLUMNS: list[Any] = list(HealthSample.__table__.columns)
_NAMES = [column.name for column in _COLUMNS]


async def write(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Insert these samples (column → value; a missing one: its default)."""
    if not rows:
        return
    connection = await session.connection()
    if connection.dialect.name != "postgresql":
        for part in chunks(rows):
            await session.execute(insert(HealthSample), part)
        return
    await session.flush()  # anything pending (a new metric) goes first
    raw = (await connection.get_raw_connection()).driver_connection
    if raw is None:  # never: a pooled asyncpg connection
        raise RuntimeError("no asyncpg connection")
    await raw.copy_records_to_table(
        HealthSample.__tablename__,
        records=[_record(row) for row in rows],
        columns=_NAMES,
    )


def _record(row: dict[str, Any]) -> tuple[Any, ...]:
    """The row in column order, a column's default where it is missing."""
    return tuple(
        row[column.name] if column.name in row else _default(column)
        for column in _COLUMNS
    )


def _default(column: Column[Any]) -> Any:
    """What SQLAlchemy would have put: the column's Python default."""
    default = column.default
    if default is None:
        return None
    arg: Any = getattr(default, "arg", None)
    return arg(None) if getattr(default, "is_callable", False) else arg
