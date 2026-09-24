# Data model

The core is a **metric registry** plus a **polymorphic, typed measurement**
store. Adding a metric is an insert into `metric_definitions`; no migration.
Values live in typed columns (not free text) so they stay queryable and
aggregable. Derived and rolling values are **computed on read** (§5.3).

```mermaid
erDiagram
  users ||--o{ api_tokens : owns
  users ||--o{ auth_sessions : has
  users ||--o{ events : records
  users ||--o{ measurements : records
  users ||--o{ photos : records
  users ||--o{ reports : generates
  users ||--o{ ingest_mappings : overrides
  metric_definitions ||--o{ measurements : typed_by
  metric_definitions ||--o{ health_samples : typed_by
  users ||--o{ health_samples : records
  events ||--o{ measurements : groups
  api_tokens ||--o{ measurements : sourced_by
  photos ||--o{ photo_analyses : analysed_by
  users ||--o{ medical_documents : uploads
  users ||--o{ conditions : declares
  users ||--o{ treatments : follows
  users ||--o{ appointments : has
  treatments |o--o{ medication_intakes : dosed_by
  users ||--o{ medication_intakes : records
  users ||--o{ meals : logs
  users ||--o{ foods : keeps
  users ||--o{ work_sessions : clocks
  users ||--o{ absences : declares
  users ||--o{ evidence : keeps
  absences |o--o{ evidence : supported_by
  meals |o--o{ evidence : logged_as

  users {
    string id PK
    string email UK
    string display_name
    string role
    string timezone
    string unit_system
    bool is_active
    string mfa_secret
    bool mfa_enabled
  }
  metric_definitions {
    string id PK
    string key UK
    string data_type
    string source
    string aggregation_hint
    string formula
    bool is_active
  }
  measurements {
    string id PK
    string user_id FK
    string metric_id FK
    string event_id FK
    datetime recorded_at
    date date_key
    float value_num
    bool value_bool
    string value_text
    time value_time
    json value_json
    string source
    string token_id FK
  }
  events {
    string id PK
    string type
    date date_key
    json meta
  }
  medication_intakes {
    string id PK
    string treatment_id FK
    string name
    string dose
    datetime taken_at
    date date_key
    string status
    string source
    string token_id
    datetime created_at
  }
  meals {
    string id PK
    datetime eaten_at
    date date_key
    string meal_type
    json photos
    json foods
    string analysis_status
    json analysis
  }
  evidence {
    string id PK
    datetime occurred_at
    string kind
    string meal_id FK
    string absence_id FK
    string sha256
  }
```

`meals.foods` points at `foods` rows by id inside a JSON list (no foreign
key): deleting a food leaves the meals already read as they are.

## Fixed tables

Baseline (migration `0001`): `users`, `api_tokens`, `auth_sessions`,
`metric_definitions`, `events`, `measurements`, `photos`,
`photo_analyses`, `automations`, `reports`, `audit_log`. Their columns
follow the specification §5.2 (plus `auth_sessions`, see
[ADR‑0003](adr/0003-refresh-sessions.md)), with these worth knowing:

- `users` — `email` (unique), `display_name`, `password_hash`, `role`
  (`admin` — the hub's administrator: updates, shared metric catalogue —
  or `user`), `timezone` (`Europe/Paris` by default: every local day is
  computed in it), `unit_system` (`metric`), `is_active` (an inactive
  account can neither log in nor use its tokens), `mfa_secret` /
  `mfa_enabled` (optional TOTP, migration `0003`).
- `measurements` — besides the typed value columns: `recorded_at` (the
  time sent with the value, else when it was written), `date_key` (the
  day it belongs to), `source` (who wrote it: `manual`, `watch`, `work`…)
  and `token_id` (the API token it came through, `NULL` for the web
  session; set to `NULL` if the token is deleted).
- `reports` — `type`, `period_start` / `period_end`, `params`, `status`,
  `file_path`; `summary` (JSON: the AI clinical synthesis — sections,
  facts, rejected sentences; migration `0009`) and `sha256` (hash of the
  generated file, indexed: `POST /reports/verify` finds a copy by it;
  reports made before migration `0020` have none).

Added by later migrations (each creates only its own tables, ADR‑0004):

- `ingest_mappings` (`0002`) — external key → metric key per source
  (`watch`, `ppc`); `user_id NULL` is a global default, a user row
  overrides it.
- `medical_documents` (`0006`) — `kind`, `title`, `doc_date`,
  `file_path` (encrypted file on disk), `media_type`, `size_bytes`,
  `notes`; `analysis_status` (`NULL` never read, `queued`, `running`,
  `done`, `failed`) and `analysis` (JSON: type, summary, grounded values,
  rejected proposals), migration `0008`.
- `conditions` (`0007`) — `name`, `code`, `status` (`active`,
  `resolved`, `suspected`), `onset_date`, `notes`.
- `treatments` (`0007`) — `name`, `dose`, `frequency`, `doses_per_day`
  (planned doses a day, the adherence denominator; `NULL` = as needed;
  migration `0019`), `start_date`, `end_date`, `active`, `notes`.
- `appointments` (`0007`) — `title`, `starts_at`, `ends_at`,
  `practitioner`, `location`, `notes`, `source` (`manual` or `ics`),
  `external_uid` (the `.ics` event, so a re-import does not duplicate).
- `meals` (`0010`) — `eaten_at`, `date_key`, `meal_type` (`breakfast`,
  `lunch`, `snack`, `dinner`), `description`; `price` and `vendor`
  (`0013`: set only for a meal logged from a paid trace — a delivery, a
  receipt); `photo_path` (the plate), `photos` (`0017`: up to 6 more,
  `[{"id", "path"}]` — the pack, its nutrition label), `foods` (`0017`:
  `[{"food_id", "grams"}]`, grams `NULL` = estimated or the whole
  package); `analysis_status` (`NULL`, `queued`, `running`, `done`,
  `failed`) and `analysis` (JSON: items with their grams and origin,
  checked nutrients, score and verdict).
- `foods` (`0017`, `0018`) — a user's food sheet: `name`, `brand`,
  `aliases` (other names used in a meal, comma-separated), `package_g`
  (box / sachet weight), `unit_name` / `unit_g` (« tomate » = 120 g: « 2
  tomates » in a meal is 240 g), `per_100g` (JSON: `energy_kcal`,
  `protein_g`, `carbs_g`, `sugars_g`, `fat_g`, `sat_fat_g`, `fiber_g`,
  `sodium_mg`), `note`, `source` (where the values come from:
  « étiquette », « Ciqual 2025 · code · name », « Open Food Facts ·
  barcode », « saisie »), `barcode`, `photos` (`[{"id", "kind": "pack" |
  "label", "path"}]`).
- `medication_intakes` (`0019`) — one row per dose: `treatment_id` (`SET
  NULL` when the treatment is deleted), `name` and `dose` **copied** from
  the treatment at the time (the history survives its deletion),
  `taken_at` (when taken), `date_key` (its local day), `status`
  (`taken`, or `skipped`: declared not taken), `source` (how it was
  entered: `web` for the web session, `mcp` for a `hub:full` token,
  `raccourci` for any other token — an iPhone Shortcut), `token_id` (that
  token, plain id), `note`; `created_at` is **when it was entered**, so a
  dose typed days later shows as such.
- `work_sessions` (`0011`, `0012`, `0015`) — `start_at` (`NULL`: clock-in
  missing), `end_at` (`NULL`: at work, or clock-out missing), `source`
  (`tap` — one-tap / GPS Shortcut —, `manual` — web, assistant —,
  `import`, or `edited` — times completed or fixed by hand), `note`,
  `place` (`site` or `remote`); unique `(user_id, start_at)`.
- `absences` (`0012`, `0016`) — `start_date`, `end_date`, `kind`
  (`arret_maladie`, `accident_travail`, `maladie_pro`, `conge`, `repos` —
  RTT, time off in lieu —, `autre`), `cause`, `note`, `start_half` (`am`,
  or `pm`: from the afternoon of the first day) and `end_half` (`pm`, or
  `am`: until noon of the last day) — a half day counts ½.
- `evidence` (`0012`, `0013`, `0014`) — proofs and traces:
  `occurred_at`, `time_known` (false when only the day is known, e.g. an
  expense line, until a receipt of the same day and amount gives the
  time), `ended_at` (parking exit, taxi drop-off, hotel check-out),
  `kind` (proofs `appel`, `sms`, `mail`, `capture`, `note`, `document`,
  `autre`; traces `transport`, `taxi`, `parking`, `livraison`, `repas`,
  `hotel`, `frais`, `activite` — see `services/evidence.py`), `place`,
  `amount`, `currency` (`EUR`), `meal_id` (the meal a delivered or bought
  meal was logged as), `title`, `description`, `count` (how many events
  it stands for: 12 calls on one screenshot), `file_path`, `file_name`,
  `media_type`, `size_bytes`, `sha256` (of the file as received),
  `absence_id` (the absence it supports; `SET NULL` on delete).

## Full-fidelity Apple Health tables

Added for the Apple Health import (see
[ADR‑0006](adr/0006-apple-health-import.md)). Unlike `measurements` (one
curated value per day), these keep **every** imported record:

- `health_samples` — every raw quantity/category sample (metric, exact
  `start_at`, value, unit, device); millions of rows, indexed
  `(user_id, metric_id, start_at)`.
- `workouts` — one row per session (type, duration, energy, distance).
- `ecg_records` — ECG metadata (classification, rate, sample count) with
  the voltage CSV stored encrypted on disk; poor-quality traces are
  skipped at import.
- `route_files` — GPS route metadata; the GPX stays on disk.
- `clinical_observations` / `clinical_documents` — observations parsed
  from the CDA document, plus the stored raw `export_cda.xml`.
- `import_jobs` — background import status and progress.

These are additive (migrations `0004`, `0005`); the daily roll-ups written
into `measurements` remain the dashboards' plottable cache.

## Idempotency (zero redundancy)

A measurement is unique per `(user_id, metric_id, date_key, event_id)`.
Two partial unique indexes enforce it (one for daily entries where
`event_id IS NULL`, one for event‑scoped rows). Writes **upsert**: recording
the same metric for the same day updates the row instead of duplicating it.

## Value routing

| `data_type` | Stored in |
|-------------|-----------|
| `int`, `float`, `duration`, `score` | `value_num` |
| `bool` | `value_bool` |
| `time` | `value_time` |
| `text`, `enum` | `value_text` |
| (object) | `value_json` |

See [`services/measurement_values.py`](../backend/app/services/measurement_values.py).

## Derived metrics

Metrics with `source = "derived"` carry a `formula` and are **read‑only**
through the write API. Examples from the catalogue: `hydration.liters =
water.bottles_1_5 * 1.5`, `workout.recovery_delta = workout.hr_max -
workout.hr_recovery_1min`.
