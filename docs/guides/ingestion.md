# Guide — ingestion (Apple Watch, CPAP, capture)

The `/ingest/*` and `/capture` endpoints are implemented (Phase 3). Samples
are mapped to metrics through a **configurable table** (`ingest_mappings`),
so new HealthKit/CPAP fields are absorbed with no code change.

## Apple Watch → `/ingest/watch`

A sample is keyed either by `metric_key` (direct) or by `healthkit_type`
(resolved through the mapping table):

```bash
curl -s $BASE/ingest/watch -H "Authorization: Bearer $WATCH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"date_key":"2026-01-15","samples":[
        {"healthkit_type":"HKQuantityTypeIdentifierOxygenSaturation",
         "value":91,"ts":"2026-01-15T04:12:00Z"},
        {"metric_key":"sleep.total","value":437}
      ]}'
# → {"recorded": 2, "skipped": []}   (unresolved keys are reported, not fatal)
```

CPAP data uses the same shape at `/ingest/ppc` (scope `ingest:ppc`).

## Managing mappings

```bash
# List your mappings + the global defaults
curl -s $BASE/ingest/mappings -H "Authorization: Bearer $ACCESS"

# Add/override a mapping at runtime (no code change)
curl -s $BASE/ingest/mappings -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"source":"watch","external_key":"HKMyCustomType",
       "metric_key":"sleep.hrv"}'
```

## Mode B — `/capture`

Triggered by an NFC tag / Shortcut / button. Opens a `capture_session`
event, records the weight and photo flags, and returns the night's
pre‑filled Watch/CPAP data plus the manual‑only complement form:

```bash
curl -s $BASE/capture -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"weight":86.4,"photo_face":true,"photo_profil":true}'
# → { "event_id": "...", "prefilled": [ ...watch/cpap... ],
#     "complement": [ ...active manual metrics to fill... ] }
```

The actual photo upload + AI analysis attach to this event in Phase 4.

## Also works: scoped tokens + batch measurements

The generic batch endpoint remains available for any script — it is the same
idempotent path the ingestion endpoints build on.

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
