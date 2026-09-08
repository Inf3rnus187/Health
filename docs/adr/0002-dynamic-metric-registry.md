# ADR 0002 — Dynamic metric registry with polymorphic measurements

- Status: accepted
- Date: 2026-01

## Context

A hard requirement is adding a new metric **without a schema migration or
redeploy**, while keeping values queryable and aggregable (not all‑text) and
storing each value exactly once (§1, §5).

## Decision

- A `metric_definitions` table is the registry. Adding a field is an insert.
- Measurements are stored in one fact table with **typed value columns**
  (`value_num`, `value_bool`, `value_text`, `value_time`, `value_json`). The
  metric's `data_type` decides which column a value routes to.
- Derived values (`source = derived`, with a `formula`) and rolling
  aggregates are **computed on read**, never stored — one source of truth.
- Idempotency is enforced by partial unique indexes on
  `(user, metric, date_key[, event])`; writes upsert.

## Consequences

- New metrics are live immediately, from UI, API or the AI.
- Values remain SQL‑queryable and aggregable per type.
- Formula evaluation for arbitrary derived metrics is deferred to the phase
  that needs it; the catalogue's derived metrics are documented by formula.
- The alternative (a column per metric, or a single JSON blob) was rejected:
  the former needs migrations, the latter loses typed querying.
