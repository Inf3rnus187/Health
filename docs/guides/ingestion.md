# Guide — ingestion (Apple Watch, CPAP, capture)

> The dedicated `/ingest/*` and `/capture` endpoints land in **Phase 3**.
> This guide documents the intended contract and what already works today.

## Today: scoped tokens + batch measurements

Any script or Shortcut can already write through the generic batch endpoint
with a scoped token — this is the same idempotent path the ingestion
endpoints will build on.

1. Create a token (scopes `ingest:watch`, `write:measurements`):

   ```bash
   curl -s $BASE/tokens -H "Authorization: Bearer $ACCESS" \
     -H 'Content-Type: application/json' \
     -d '{"name":"apple-watch","scopes":["ingest:watch","write:measurements"]}'
   ```

2. From an iOS Shortcut, POST the night's samples:

   ```bash
   curl -s $BASE/measurements -H "Authorization: Bearer $WATCH_TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"items":[
           {"metric_key":"sleep.spo2_min","date_key":"2026-01-15","value":89},
           {"metric_key":"sleep.total","date_key":"2026-01-15","value":437}
         ]}'
   ```

Idempotency means re‑sending the same day is safe (values update in place).

## Phase 3 contract (planned)

- `POST /ingest/watch` — `{ date_key, samples: [{ metric_key | healthkit_type,
  value, unit, ts }] }`, mapped to metrics via a configurable HealthKit table.
- `POST /ingest/ppc` — CPAP machine data (hours, AHI, leaks, pressure).
- `POST /capture` — mode B: opens a `capture_session` event, attaches the
  day's photo, reads the weight, pre‑fills Watch data, and returns the
  manual‑only complement form.
