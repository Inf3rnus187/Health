"""Raw samples counted per user, metric and source, kept exact by the database.

The inventory (Données) shows, for each metric and source, how many raw
samples there are and their first and last dates. Counting millions of
rows took 0.3 s at each view; ``sample_counts`` holds the answer and
triggers on ``health_samples`` keep it exact in the same transaction as
every insert, update or delete — whatever writes (import, sync, merge,
delete, account deletion), since the database itself does it.

PostgreSQL: one statement-level trigger per operation, reading the rows
the statement changed (transition tables): an import of 5 000 rows
updates a few count rows once (rows are written by ``COPY``,
:mod:`app.services.sample_writes`). A delete that removes a group's
first or last sample reads **that** bound again, and only that one,
through ``ix_samples_user_metric_start``: a sync replacing its latest
sums reads the last date back from the end (a few ms), never the first
date, which the index (without the source) could only reach after every
older sample of the other sources (160–180 ms on 930 000 samples, at
every sync — migration 0029). SQLite (tests): the same rules, row by
row.

Not an ORM table of ``Base.metadata``: created and dropped with
``health_samples`` (below) and by migration 0027, so a new samples table
always starts with empty counts. No foreign key: deleting an account
deletes its samples, and the triggers then remove their counts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    event,
    text,
)

from app.models.health_raw import HealthSample

counts = Table(
    "sample_counts",
    MetaData(),
    Column("user_id", String(36), primary_key=True),
    Column("metric_id", String(36), primary_key=True),
    Column("source", String(32), primary_key=True),
    Column("n", BigInteger, nullable=False),
    Column("first_at", DateTime(timezone=True)),
    Column("last_at", DateTime(timezone=True)),
)

_TABLE = """
CREATE TABLE IF NOT EXISTS sample_counts (
    user_id VARCHAR(36) NOT NULL,
    metric_id VARCHAR(36) NOT NULL,
    source VARCHAR(32) NOT NULL,
    n BIGINT NOT NULL,
    first_at {stamp},
    last_at {stamp},
    PRIMARY KEY (user_id, metric_id, source)
)"""

_PG_FUNCTION = """
CREATE OR REPLACE FUNCTION sample_counts_sync() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('DELETE', 'UPDATE') THEN
        UPDATE sample_counts c SET
            n = c.n - g.n,
            first_at = CASE WHEN g.lo <= c.first_at THEN NULL
                            ELSE c.first_at END,
            last_at = CASE WHEN g.hi >= c.last_at THEN NULL
                           ELSE c.last_at END
        FROM (SELECT user_id, metric_id, source, count(*) AS n,
                     min(start_at) AS lo, max(start_at) AS hi
              FROM old_rows GROUP BY user_id, metric_id, source) g
        WHERE c.user_id = g.user_id AND c.metric_id = g.metric_id
          AND c.source = g.source;
        DELETE FROM sample_counts WHERE n <= 0;
        UPDATE sample_counts c SET
            first_at = coalesce(c.first_at,
                (SELECT min(s.start_at) FROM health_samples s
                 WHERE s.user_id = c.user_id AND s.metric_id = c.metric_id
                   AND s.source = c.source)),
            last_at = coalesce(c.last_at,
                (SELECT max(s.start_at) FROM health_samples s
                 WHERE s.user_id = c.user_id AND s.metric_id = c.metric_id
                   AND s.source = c.source))
        WHERE c.first_at IS NULL OR c.last_at IS NULL;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        INSERT INTO sample_counts AS c
            (user_id, metric_id, source, n, first_at, last_at)
        SELECT user_id, metric_id, source, count(*), min(start_at),
               max(start_at)
        FROM new_rows GROUP BY user_id, metric_id, source
        ORDER BY user_id, metric_id, source
        ON CONFLICT (user_id, metric_id, source) DO UPDATE SET
            n = c.n + excluded.n,
            first_at = least(c.first_at, excluded.first_at),
            last_at = greatest(c.last_at, excluded.last_at);
    END IF;
    RETURN NULL;
END $$"""

_PG_CLEAR = """
CREATE OR REPLACE FUNCTION sample_counts_clear() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM sample_counts;
    RETURN NULL;
END $$"""

_PG_TRIGGERS = (
    ("sample_counts_ins", "INSERT", "NEW TABLE AS new_rows"),
    (
        "sample_counts_upd",
        "UPDATE",
        "OLD TABLE AS old_rows NEW TABLE AS new_rows",
    ),
    ("sample_counts_del", "DELETE", "OLD TABLE AS old_rows"),
)

#: The count row of the sample ``old`` (SQLite trigger).
_LITE_SAME = (
    "user_id = old.user_id AND metric_id = old.metric_id "
    "AND source = old.source"
)
_LITE_ADD = """
    INSERT INTO sample_counts
        (user_id, metric_id, source, n, first_at, last_at)
    VALUES (new.user_id, new.metric_id, new.source, 1, new.start_at,
            new.start_at)
    ON CONFLICT (user_id, metric_id, source) DO UPDATE SET
        n = n + 1,
        first_at = min(first_at, excluded.first_at),
        last_at = max(last_at, excluded.last_at);"""
_LITE_REMOVE = """
    UPDATE sample_counts SET n = n - 1 WHERE {same};
    DELETE FROM sample_counts WHERE {same} AND n <= 0;
    UPDATE sample_counts SET
        first_at = (SELECT min(s.start_at) FROM health_samples s
                    WHERE s.user_id = old.user_id
                      AND s.metric_id = old.metric_id
                      AND s.source = old.source)
    WHERE {same} AND old.start_at <= first_at;
    UPDATE sample_counts SET
        last_at = (SELECT max(s.start_at) FROM health_samples s
                   WHERE s.user_id = old.user_id
                     AND s.metric_id = old.metric_id
                     AND s.source = old.source)
    WHERE {same} AND old.start_at >= last_at;"""


#: The counts computed from the samples themselves (a rebuild).
REFILL = """
INSERT INTO sample_counts (user_id, metric_id, source, n, first_at, last_at)
SELECT user_id, metric_id, source, count(*), min(start_at), max(start_at)
FROM health_samples {where}
GROUP BY user_id, metric_id, source"""


def postgresql() -> list[str]:
    """The table, its functions and the triggers (PostgreSQL)."""
    out = [_TABLE.format(stamp="TIMESTAMP WITH TIME ZONE"), _PG_FUNCTION]
    out.append(_PG_CLEAR)
    for name, event_name, rows in _PG_TRIGGERS:
        out.append(f"DROP TRIGGER IF EXISTS {name} ON health_samples")
        out.append(
            f"CREATE TRIGGER {name} AFTER {event_name} ON health_samples "
            f"REFERENCING {rows} FOR EACH STATEMENT "
            "EXECUTE FUNCTION sample_counts_sync()"
        )
    out.append("DROP TRIGGER IF EXISTS sample_counts_trunc ON health_samples")
    out.append(
        "CREATE TRIGGER sample_counts_trunc AFTER TRUNCATE ON health_samples "
        "FOR EACH STATEMENT EXECUTE FUNCTION sample_counts_clear()"
    )
    return out


def sqlite() -> list[str]:
    """The table and the triggers, row by row (SQLite, tests)."""
    remove = _LITE_REMOVE.format(same=_LITE_SAME)
    return [
        _TABLE.format(stamp="DATETIME"),
        "CREATE TRIGGER IF NOT EXISTS sample_counts_ins AFTER INSERT ON "
        f"health_samples BEGIN {_LITE_ADD} END",
        "CREATE TRIGGER IF NOT EXISTS sample_counts_del AFTER DELETE ON "
        f"health_samples BEGIN {remove} END",
        "CREATE TRIGGER IF NOT EXISTS sample_counts_upd AFTER UPDATE OF "
        "user_id, metric_id, source, start_at ON health_samples "
        f"BEGIN {remove} {_LITE_ADD} END",
    ]


@event.listens_for(HealthSample.__table__, "after_create")
def _created(_: Any, connection: Any, **__: Any) -> None:
    """A new samples table: its counts table, empty, and the triggers."""
    dialect = connection.dialect.name
    statements = postgresql() if dialect == "postgresql" else sqlite()
    for statement in statements:
        connection.execute(text(statement))
    connection.execute(text("DELETE FROM sample_counts"))


@event.listens_for(HealthSample.__table__, "before_drop")
def _dropped(_: Any, connection: Any, **__: Any) -> None:
    """The samples table goes: its counts too (its triggers go with it)."""
    connection.execute(text("DROP TABLE IF EXISTS sample_counts"))
