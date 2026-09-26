# Guide — ingestion (Apple Santé, Health Auto Export, montre, PPC, capture)

Every channel writes the **same canonical metric** for the same concept
(e.g. `body.weight`, `activity.steps`, `bio.hba1c`), resolved through the
full HealthKit catalog (iOS 26 SDK: 121 quantity + 72 category types) and a
**configurable mapping table** (`ingest_mappings`). Raw samples are kept;
daily values are rebuilt from them with one rule (one Apple channel per
day — native export, Health Auto Export and the iPhone app are never
added up — plus the other sources). Required token scope per route:
[API reference](../api.md).

| Channel | Route | Token scope |
|---------|-------|-------------|
| Full Apple Health export (`export.zip`) | `POST /imports/apple-health` | `write:measurements` (+ `?token=`) |
| Your own iPhone app reading HealthKit: samples by UUID, cumulative sums, sleep, workouts, deletions ([below](#iphone-app-healthkit--synchealthkit)); `GET` = what the hub holds | `POST /sync/healthkit`, `GET /sync/healthkit` | `write:measurements` (header only) |
| Health Auto Export (daily JSON) | `POST /sync/auto-export` | `write:measurements` (+ `?token=`) |
| SimpleHealthExportCSV (zip of CSV) | `POST /imports/apple-health` | `write:measurements` (+ `?token=`) |
| iPhone Shortcut (flat map) | `POST /sync/health` | `ingest:watch` |
| One-tap counts: `{"metric": key, "amount"?, "date_key"?}` — water bottle, coffee, cigarette, urge broken, pee (`elimination.urination`, timed), clock in / out (`work.start`, `work.remote_start`, `work.end`, `work.remote_end`). `amount`: `1` by default, negative takes back, `0` confirms a day at zero (a value 0 is stored, instead of a day without data); `date_key`: today (local) by default — pees and clock taps only accept today, and clock taps only `amount` 1 | `POST /sync/tally` | `write:measurements` (+ `?token=`) |
| Clock in / out: JSON `kind` (`in` / `out`), `at`? (ISO; default now, without offset = local), `place`? (`site` default / `remote`; a clock-out closes the open session wherever it is) | `POST /work/clock` | `write:measurements` (+ `?token=`) |
| Past clock-in / clock-out logs (txt, csv, json; `?dry_run=true` reads only) | `POST /work/import` | `write:measurements` (+ `?token=`) |
| App exports and receipts as traces — Uber, Uber Eats, Navigo, parking, hotels, expense reports, bank statements (CSV / XLSX / JSON), receipts (PDF, photo), Lucca expense-report PDFs (one trace per expense, the PDF kept untouched), ticket exports (NinjaOne… CSV: the `person`'s actions, one `activite` trace a day), WhatsApp chat exports (`.txt`: the `person`'s messages and calls). Multipart `files` + `kinds` (one per file, same order: `transport`, `taxi`, `parking`, `livraison`, `repas`, `hotel`, `frais`, `activite` or `auto` — guessed), form `person`? (whose tickets / messages; default the most active author, or « Moi » in a chat — the preview lists the others); a receipt and its expense line are merged; `?meals=true` logs deliveries and bought meals as priced meals, `?dry_run=true` reads only | `POST /traces/import` | session or `hub:full` |
| One proof or trace by hand: multipart `occurred_at`* (ISO; without offset = local), `kind` (`capture` by default; proofs `appel`, `sms`, `mail`, `capture`, `note`, `document`, `autre`, or a trace kind above), `title`, `description`, `count` (1–10000), `absence_id`, `file` (30 MB in the API, 25 MB through nginx), trace fields `ended_at`, `place`, `amount`, `currency` (`EUR`), `meal=true` (a `livraison` / `repas` trace is also logged as a priced meal and read by the AI) | `POST /evidence` | session or `hub:full` |
| Absences from an HR export (Lucca…: CSV, XLSX, JSON): multipart `files`, form `person`? (a manager's export; default the one with the most rows), `?dry_run=true` reads only; nothing added twice | `POST /absences/import` | session or `hub:full` |
| A night the watch missed: JSON `bedtime`, `wake_time` (ISO; without offset = local; 20 h at most), `awakenings`? (0–100) — a raw `manual` sleep sample plus that day's `sleep.asleep` | `POST /sleep/nights` (`DELETE /sleep/nights/{id}`) | session or `hub:full` |
| iPhone Shortcut histories — one time stamp per line, one kind per file (`files` + optional `keys`; clock-ins and clock-outs paired, counters fill empty days, pee de-duplicated) | `POST /logs/import` | `write:measurements` (+ `?token=`) |
| Watch / HealthKit samples | `POST /ingest/watch` | `ingest:watch` |
| CPAP | `POST /ingest/ppc` | `ingest:ppc` |
| Progress photos | `POST /ingest/photo` | `ingest:photo` |
| Pee at a given time (web Journal, `{"at": …}`) | `POST /journal/urination` | `write:measurements` (+ `?token=`) |
| Meal: form `description`, `file` (plate photo), `photos` (repeated, up to 6: box, sachet, nutrition table), `foods` (JSON `[{"food_id","grams"}]`), `meal_type`?, `eaten_at`? | `POST /meals` (multipart) | `write:measurements` (+ `?token=`) |
| Meal changed afterwards: fields and foods | `PUT /meals/{id}` (JSON) | `write:measurements` |
| Medication dose by name (iPhone Shortcut): JSON `treatment` (accents and case ignored; the start of a word, 3 letters or more, is enough), `taken_at`? (never more than 10 min ahead), `status`? (`taken`/`skipped`), `dose`? (default: the treatment's), `note`? | `POST /medications/take` | `write:measurements` (+ `?token=`) |
| Medication dose of a treatment (web): same JSON without `treatment` | `POST /treatments/{id}/intakes` | `write:measurements` (+ `?token=`) |
| Meal photo added afterwards (the plate's when it has none) / removed | `POST /meals/{id}/photos` (multipart `file`), `DELETE /meals/{id}/photo`, `DELETE /meals/{id}/photos/{photo_id}` — `?read=false` to change several, then read once | `write:measurements` |
| Food sheet (« Mes aliments »): JSON `name`*, `brand`, `aliases` (comma-separated), `package_g`, `unit_name` / `unit_g` (« tomate », 120), `portion_g` (usually eaten, g: counted when a meal gives no quantity), `per_100g` (`energy_kcal`, `protein_g`, `carbs_g`, `sugars_g`, `fat_g`, `sat_fat_g`, `fiber_g`, `sodium_mg`), `note`, `source`, `barcode` (digits), `product_info` (Open Food Facts' details, as `GET /openfoodfacts/{barcode}` gives them; send them back unchanged when editing) | `POST /foods`, `PUT /foods/{id}`, `DELETE /foods/{id}` (`GET /foods`: `read:all`) | `write:measurements` |
| Food photo: multipart `file`, form `kind` (`pack` default, or `label`) | `POST /foods/{id}/photos`, `DELETE /foods/{id}/photos/{photo_id}` | `write:measurements` |
| Read a sheet's Open Food Facts page again by its barcode (no pack to scan): values it gives, product details, package / brand when empty; the user's fields kept → the sheet and `changed`. All sheets with a barcode (a minute at most) → `updated`, `unchanged`, `failed`, `remaining`. Needs `FOOD_LOOKUP_ONLINE=true` | `POST /foods/{id}/refresh`, `POST /foods/refresh` | `write:measurements` |
| Read a pack or its nutrition table with the vision model: multipart `file` → a proposal (`name`, `brand`, `package_g`, `per_100g`), nothing saved; runs inside the API, 100 s at most | `POST /foods/read-label` | `write:measurements` |
| Ciqual 2025 reference values (offline table): `?q=` (2–100 characters, every word must match), `limit` (1–50, default 20); one food by code | `GET /ciqual`, `GET /ciqual/{code}` | `read:all` |
| A pack's barcode read on a photo (camera or gallery), decoded on the hub offline (EAN-13, EAN-8, UPC): multipart `file` → `barcodes`, `food` (my food with that barcode or null), `product` (Open Food Facts proposal only when `FOOD_LOOKUP_ONLINE=true`, else null), `online`, `note`. Nothing saved, the photo is not kept | `POST /foods/scan` | `write:measurements` (+ `?token=`) |
| Food stock move: JSON `food_id` / `barcode` / `food` (name; a word's start is enough, two sizes answering it → `422`), `kind` (`purchase` default, `out`: thrown or given, `count`: what is left now), one of `packs` (× package; a purchase without quantity = 1 pack), `units` (× unit), `grams`, `at`?, `note`? → the move and the food's level. Meals are never entered: their analysed lines deduct by themselves | `POST /stock` | `write:measurements` (+ `?token=`) |
| Food stock: level per food (`grams`, `packs`, `units`, `portions`, `missing`, `eaten_g`), a food's history (moves and meals), undo a move | `GET /stock`, `GET /stock/{food_id}/moves` (`read:all`), `DELETE /stock/moves/{id}` | `write:measurements` |
| A packaged food by barcode (8–14 digits) from Open Food Facts → a proposal, nothing saved: name, brand, weight, 8 values (sodium as given) and `product_info` (ingredients, allergens, traces, additives, Nutri-Score, NOVA, fruits/vegetables %, levels, labels, categories, serving, other nutrients per 100 g, page URL). Off by default: `422` unless `FOOD_LOOKUP_ONLINE=true`; only the barcode is sent | `GET /openfoodfacts/{barcode}` | `write:measurements` |
| Any script (sets — **replaces** — a day's value) | `POST /measurements` | `write:measurements` |

iPhone Shortcuts step by step (one token, one rule for every count, one
for meals): [usage guide](utilisation.md#raccourcis-iphone--une-seule-règle).

## Upload size limits

- **nginx** (`nginx/default.conf`) caps every request body at **25 MB**
  (`client_max_body_size 25m`: all the files of one request together),
  except `POST /imports/apple-health` (no limit, streamed to disk, 1 h
  timeouts) and `POST /sync/auto-export` (no limit, 10 min).
- **Photos** — progress photos, meal photos (each one), food photos:
  `MAX_UPLOAD_MB` (15 by default) per image, checked by the API.
- **Evidence files** (`POST /evidence`): 30 MB in the API, so 25 MB in
  practice behind nginx; medical documents: 25 MB.
- A body over the nginx cap is refused by nginx (`413`) before it
  reaches the API.

## iPhone app (HealthKit) → `/sync/healthkit`

For an app of your own reading HealthKit on the iPhone: every sample
type, incremental, by HealthKit UUID. Web app › **Import › « App iPhone
(HealthKit) » › Créer un jeton pour l'app** mints a `write:measurements`
token; the app sends it **in the header only** —
`Authorization: Bearer <token>` (a `?token=` in the URL is refused).

```bash
curl -s $BASE/sync/healthkit -H "Authorization: Bearer $APP_TOKEN" \
  -H 'Content-Type: application/json' -d '{
  "samples": [
    {"uuid": "6F1C…", "type": "HKQuantityTypeIdentifierHeartRate",
     "start": "2026-09-26T08:00:00+02:00", "end": "2026-09-26T08:00:00+02:00",
     "value": 72, "unit": "count/min", "device": "Apple Watch"},
    {"uuid": "9A02…", "type": "HKQuantityTypeIdentifierOxygenSaturation",
     "start": "2026-09-26T04:03:00+02:00", "value": 0.97, "unit": "%"},
    {"uuid": "C3D4…", "type": "HKCategoryTypeIdentifierSleepAnalysis",
     "start": "2026-09-26T01:00:00+02:00", "end": "2026-09-26T02:00:00+02:00",
     "value": 4, "device": "Apple Watch"},
    {"uuid": "E5F6…", "type": "HKCategoryTypeIdentifierHeadache",
     "start": "2026-09-26T09:00:00+02:00", "end": "2026-09-26T10:00:00+02:00",
     "value": "HKCategoryValueSeverityModerate"}
  ],
  "statistics": [
    {"type": "HKQuantityTypeIdentifierStepCount",
     "start": "2026-09-26T08:00:00+02:00", "end": "2026-09-26T09:00:00+02:00",
     "sum": 412, "unit": "count"}
  ],
  "workouts": [
    {"uuid": "0B1C…", "activity": "HKWorkoutActivityTypeWalking",
     "start": "2026-09-26T18:00:00+02:00", "end": "2026-09-26T18:45:00+02:00",
     "energy_kcal": 210, "distance_km": 3.1}
  ],
  "deleted": ["1A2B…"]
}'
# → {"samples": 4, "statistics": 1, "workouts": 1, "deleted": 1,
#    "days": 12, "skipped": []}
```

Every list is optional; per request at most 5000 `samples`, 5000
`statistics`, 500 `workouts`, 5000 `deleted` (and 25 MB through nginx).
Dates are ISO 8601; without an offset they are the user's local time.

**`samples`** — one HealthKit sample each (`HKQuantitySample`,
`HKCategorySample`), keyed by its `uuid` (`sample.uuid.uuidString`): sent
again, it replaces itself; nothing is ever added twice.

| Kind | `value` | `unit` |
|------|---------|--------|
| Discrete quantity (`aggregationStyle` discrete: heart rate, HRV, SpO2, weight, blood pressure's systolic and diastolic samples, glucose, temperature…) | HealthKit's own number: `quantity.doubleValue(for: unit)` — 0.97 for 97 % | the `HKUnit` string (`count/min`, `ms`, `%`, `kg`, `mmHg`, `mg/dL`, `degC`…), converted to the metric's unit |
| Sleep (`HKCategoryTypeIdentifierSleepAnalysis`) | `sample.value` as is: 0 in bed, 1 asleep (unspecified), 2 awake, 3 core, 4 deep, 5 REM — or the name (`HKCategoryValueSleepAnalysisAsleepDeep`, `asleepDeep`); `end` required | — |
| Another category | its `HKCategoryValue…` name as in Apple's `export.xml` (`HKCategoryValueSeverityMild`, `HKCategoryValueAppleStandHourStood`…); none for an event that counts (notifications, hand-washing…); `end` for one that lasts (mindfulness: its minutes) | — |

`device` is the recording device (`sample.device?.name`, else
`sourceRevision.source.name`). A **cumulative** quantity (steps, distance,
active or resting energy, flights, exercise minutes, nutrition, water…)
is **refused here**: the iPhone and the watch record the same steps, and
only HealthKit's statistics count them once — send it in `statistics`.

**`statistics`** — cumulative types as HealthKit adds them up:
`HKStatisticsCollectionQuery` with `.cumulativeSum` and an hourly
`intervalComponents`, one entry per hour that has a `sumQuantity()`
(`type`, `start`, `end`, `sum`, `unit`). A batch replaces the sums it
overlaps for that type: send today (and yesterday, for late watch syncs)
again at each sync; changing from hours to days never adds twice. A
discrete type sent here is refused.

**Sleep** — the stages make the **nights** (wake-up day, 18:00 cut:
bedtime, wake-up, awakenings) of Travail › Dossier travail et santé ›
Nuits, and the daily `sleep.asleep` (core + deep + REM +
unspecified), `sleep.core`, `sleep.deep`, `sleep.rem`, `sleep.awake`,
`sleep.time_in_bed`. The **phases come from the Apple Watch** (a
`device` whose name holds « Watch »: send `sample.device?.name`); only a
night the watch did not record (not worn, battery flat) takes another
recorder's (an app), the one with the most sleep — never several added.
**Time in bed** comes from every device that writes it (the iPhone's
bedtime schedule), overlaps merged.

**`workouts`** — `uuid`, `activity` (`HKWorkoutActivityTypeWalking`, or
`walking`), `start`, `end`, optional `duration_min` (else end − start),
`energy_kcal`, `distance_km`. They join the native export's workouts;
a day's `workout.count`, `workout.total_min`, `workout.energy`,
`workout.distance` come from one channel (the one with most sessions).

**`deleted`** — the UUIDs of `HKAnchoredObjectQuery`'s deleted objects
(samples or workouts): removed, their days recomputed; a day left
without any sample loses the value this channel gave it.

**Answer** — how many `samples`, `statistics`, `workouts` were stored,
`deleted` removed, `days` of daily values recomputed, and `skipped`:
`{"type", "reason", "count"}` for each kind of line refused (unknown
type, cumulative sent as a sample, discrete as a sum, sleep without
`end` or with a value outside 0-5, category without its name…). A
refused line never fails the request.

**One channel a day** — the app's data is stored under the source
`healthkit`, which counts as a HealthKit channel with the native export
(`apple`) and Health Auto Export (`auto-export`): for each metric and
day, the channel with the most samples is taken, never their sum. Stop
Health Auto Export once the app syncs.

**Status** — `GET /sync/healthkit` (same token): `last_sync_at`,
`samples`, `workouts` and per metric `key`, `label`, `samples`, `last`
(newest sample): to resume after a reinstall (the anchors are lost).

**Suggested app flow**:

1. Ask HealthKit read authorization for the types you want.
2. First run: for each type, `HKAnchoredObjectQuery` from `nil`, sent in
   batches (5000 samples), and hourly statistics day by day, back to the
   history you want; keep each type's anchor.
3. Then at each sync (an `HKObserverQuery` with background delivery, or
   when the app opens): each type's anchored query from its anchor
   (new samples + deleted UUIDs) and today's and yesterday's hourly
   statistics; save the new anchors only after a `200`.

Not taken yet: ECG voltages, workout routes (GPS), clinical records,
samples' metadata — they still come with the full export
(`POST /imports/apple-health`).

## Health Auto Export (JSON)

The *Health Auto Export* iOS app pushes Health data on a schedule.

1. Web app › **Import › « Health Auto Export (JSON) » › Créer l'URL** — it
   mints a `write:measurements` token and shows
   `https://<hub>/api/v1/sync/auto-export?token=<token>`.
2. In the app: new **Automation** of type **REST API**, paste the URL,
   method **POST**, format **JSON**, data type **Health Metrics**, the
   metrics you want (all is fine), and a sync schedule. A first run with a
   long date range back-fills the history.

What the server does with a payload
(`{"data": {"metrics": [{"name", "units", "data": [{"date", "qty"}]}]}}`):

- every spelling the app has used for a metric maps to its HealthKit type
  (`walking_running_distance`, `weight_body_mass`, `blood_oxygen_saturation`…),
  so it lands on the same metric as the native export;
- `blood_pressure` is split into systolic / diastolic; `sleep_analysis`
  into sleep stages (`sleep.asleep`, `sleep.deep`, `sleep.rem`…, hours →
  minutes); percentages (already 0–100) are never scaled twice;
- each point is stored as a raw sample; re-pushing a day replaces that
  day's Health Auto Export samples (idempotent), and the daily values are
  recomputed from the pushed day onward;
- workouts in the payload are not imported (use the full export for them);
- a name outside the catalog is still stored, under an `apple.<name>`
  metric; points without a date or a number (`qty`, or `Avg` for heart
  rate) are listed in the response's `skipped`.

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

A `healthkit_type` that has **no mapping** is not skipped: it resolves
through the HealthKit catalog (French label, domain, unit, daily rule), or
to a synthesised `apple.*` metric for a type outside the SDK catalog. Only
samples with neither a `metric_key` nor a `healthkit_type` are reported in
`skipped`.

## iPhone Shortcut sync — `/sync/*`

A pre-filled Shortcut can be built by the API only — the web UI does
not offer it (iOS refuses unsigned `.shortcut` files, see the CSV zip
path below, which is what the web card « Synchro iPhone (export CSV) »
sets up):

```bash
# Interactive user session (JWT) only, never a token. Mints an
# ingest:watch token and returns a .shortcut file with the token +
# endpoint already embedded.
curl -s "$BASE/sync/shortcut?base=https://health.example.com" \
  -H "Authorization: Bearer $ACCESS" -o "Phoenix Sante.shortcut"
```

The Shortcut posts a **flat map** (easy to build on-device) that the
server adapts to the ingest pipeline. Values may be plain text with units
or French separators — they are parsed leniently; unparsable keys are
reported, never fatal:

```bash
curl -s $BASE/sync/health -H "Authorization: Bearer $WATCH_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"date_key":"2026-01-15","metrics":{
        "HKQuantityTypeIdentifierBodyMass":"86,2 kg",
        "HKQuantityTypeIdentifierStepCount":"8 542 pas"}}'
# → {"recorded": 2, "skipped": []}
```

`date_key` is optional (defaults to the server's today).

## iPhone → CSV zip (SimpleHealthExportCSV)

Because iOS refuses to import unsigned shortcut files (Apple signing needs
an Apple device), the reliable device path reuses an already-signed
community shortcut, **SimpleHealthExportCSV**, which exports Health data as
one CSV per HealthKit type, zipped, and can upload the zip. The web card
**Import › « Synchro iPhone (export CSV) » › « Créer l'URL d'upload »**
mints a `write:measurements` token (named « iPhone (CSV) ») and shows,
once, `https://<hub>/api/v1/imports/apple-health?token=<token>` with the
recipe; point the shortcut's upload at it:

```
POST /api/v1/imports/apple-health?token=<token>   (scope write:measurements)
Body: multipart/form-data, file field "file" = the .zip
→ 202 { id, status: "queued", ... }   # then poll GET /imports/{id}
```

The token may be given as `?token=` (handy for a Shortcut — no header to
hand-enter) **or** the usual `Authorization: Bearer <token>` header.

The importer **auto-detects** the archive: `export.xml` → Apple's native
format; otherwise it reads every `type,sourceName,…,unit,value` CSV member
into the same full-fidelity storage (`health_samples`) and daily roll-ups,
resolving each type through the HealthKit catalog. When a job ends
`done`, the reconciliation (`reconcile_data`: merge duplicate keys,
rebuild daily values from the raw data) is queued by itself — nothing to
launch by hand.

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

Photos are sent separately to `POST /ingest/photo` (multipart: `file`,
`angle` = `face` / `profil` / `dos`, optional `date_key`, `weight`) with an
`ingest:photo` token; the analysis runs in the worker.

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
