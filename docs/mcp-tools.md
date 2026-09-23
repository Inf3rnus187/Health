# Outils du serveur MCP

Généré depuis le serveur (`python -m phoenix_mcp.doc`) — ne pas éditer à
la main. Chaque outil appelle l'API REST avec le jeton `hub:full` ;
configuration et connexion d'un client : [guide MCP](guides/mcp.md).
Paramètre suivi de `*` : obligatoire ; sinon la valeur par défaut est
indiquée.

83 outils.

## Données et métriques

### `health_summary`

Home tiles: latest value, 7-day average and change per key metric.

### `list_domains`

Domain codes and their French names (Cœur, Biologie, Sommeil…).

### `list_metrics`

Metric definitions (key, label, unit, domain), optionally by domain.

Paramètres : `domain` (string | null, défaut `None`)

### `metric_overview`

One metric exactly as every page shows it.

Latest reading (time, source), last day, 7/30-day averages, 30-day
range, sources of the daily values and the daily series.

Paramètres : `key`* (string), `days` (integer, défaut `365`)

### `get_measurements`

Daily values (all sources) of a metric between two ISO dates.

Paramètres : `metric_key` (string | null, défaut `None`), `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

### `get_samples`

Raw Apple Health samples (each reading with its time and source).

Paramètres : `metric_key` (string | null, défaut `None`), `start` (string | null, défaut `None`), `end` (string | null, défaut `None`), `limit` (integer, défaut `200`), `offset` (integer, défaut `0`)

### `get_trend`

A metric bucketed by day / week / month (per its aggregation).

Paramètres : `metric_key`* (string), `bucket` (string, défaut `week`)

### `domain_dashboard`

Dashboard of a domain (body, heart, sleep, bio, habit…).

Paramètres : `domain`* (string), `window` (integer, défaut `7`)

### `daily_summary`

Every daily value of one day (default today), with metric names.

Paramètres : `date_key` (string | null, défaut `None`)

### `data_inventory`

Everything stored, per metric and source.

Raw and daily counts by source with their first/last dates: checks
that Apple, Health Auto Export and lab values agree.

### `reconcile_data`

Rebuild one truth from the stored data (no AI).

Merges duplicate keys, aligns with the HealthKit catalog and
recomputes every daily value from raw samples (in the worker).

### `add_to_counter`

ADD to a day's count: water bottles, coffees, cigarettes, pees.

Use it for "ajoute une bouteille / un café / une clope / un pipi": it
adds ``amount`` to the day's total (default: the user's today) and
never erases it. A negative amount takes back a wrong entry (never
below 0). Returns the total before (``previous``) and after
(``total``). Keys: water.bottles_1_5, habit.coffee, habit.cigarettes,
habit.urges_broken, elimination.urination (a pee is logged now; for
another time use log_urination).

Paramètres : `metric_key`* (string), `amount` (number, défaut `1`), `date_key` (string | null, défaut `None`)

### `record_measurement`

SET a metric's value for a day (weight, sleep, a symptom…).

It REPLACES the day's value: never use it to add to a count (use
add_to_counter). When the day already holds a different value it
refuses, unless ``replace`` is true — pass it only after the user
confirmed the new value. Returns the value it replaced (``previous``).

Paramètres : `metric_key`* (string), `value`* (any), `date_key` (string | null, défaut `None`), `replace` (boolean, défaut `False`)

### `delete_measurement`

Delete one recorded daily value by id.

Paramètres : `measurement_id`* (string)

### `create_metric`

Create a custom metric (e.g. habit.patches) — no migration needed.

Paramètres : `key`* (string), `label`* (string), `domain`* (string), `data_type` (string, défaut `float`), `unit` (string | null, défaut `None`), `aggregation_hint` (string, défaut `avg`)

### `update_metric`

Change a metric's label, unit, bounds, aggregation or active flag.

Paramètres : `key`* (string), `changes`* (object)

### `export_data`

Export tidy data as text (csv / json / fhir).

Paramètres : `export_format` (string, défaut `csv`), `domain` (string | null, défaut `None`), `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

## Dossier médical, Suivi, documents

### `medical_record`

The Dossier, built from the documents.

Documents with their AI reading; conditions and medications read in
documents but not declared yet (to confirm); every lab / FibroScan
result with its previous value and source document; the chronology.

### `care_overview`

Suivi: each declared condition and its indicators.

Latest value, change and series of each indicator, and the
documents mentioning the condition.

### `list_documents`

Medical documents with their AI analysis (values, summary, status).

### `document_text`

The text the AI reads from a document.

OCR for scans. Use it to check an extraction against the source.

Paramètres : `doc_id`* (string)

### `analyze_document`

(Re-)read one document with the medical models (worker, minutes).

Paramètres : `doc_id`* (string)

### `analyze_all_documents`

(Re-)read every document with the medical models.

### `upload_document`

Add a medical document, then call analyze_document.

kind: ordonnance, imagerie, compte_rendu, biologie, efr,
test_marche, vaccination or autre. ``content_base64``: the file.

Paramètres : `filename`* (string), `content_base64`* (string), `kind` (string, défaut `autre`), `title` (string, défaut ``), `doc_date` (string, défaut ``), `media_type` (string, défaut `application/pdf`)

### `delete_document`

Delete a medical document (its extracted values stay recorded).

Paramètres : `doc_id`* (string)

### `list_conditions`

Declared conditions (maladies) with status and onset.

### `save_condition`

Add a condition, or replace one by ``condition_id``.

status: active, resolved or suspected; code: ICD-10 (optional).

Paramètres : `name`* (string), `status` (string, défaut `active`), `code` (string | null, défaut `None`), `onset_date` (string | null, défaut `None`), `notes` (string | null, défaut `None`), `condition_id` (string | null, défaut `None`)

### `delete_condition`

Delete a declared condition.

Paramètres : `condition_id`* (string)

### `list_treatments`

Treatments (current and stopped) with dose, frequency and dates.

### `save_treatment`

Add a treatment, or replace one when ``treatment_id`` is given.

Paramètres : `name`* (string), `dose` (string | null, défaut `None`), `frequency` (string | null, défaut `None`), `start_date` (string | null, défaut `None`), `end_date` (string | null, défaut `None`), `active` (boolean, défaut `True`), `notes` (string | null, défaut `None`), `treatment_id` (string | null, défaut `None`)

### `delete_treatment`

Delete a treatment.

Paramètres : `treatment_id`* (string)

### `list_appointments`

Medical appointments (manual and imported from .ics).

### `add_appointment`

Add an appointment (``starts_at`` ISO datetime with offset).

Paramètres : `title`* (string), `starts_at`* (string), `practitioner` (string | null, défaut `None`), `location` (string | null, défaut `None`), `notes` (string | null, défaut `None`)

### `delete_appointment`

Delete an appointment.

Paramètres : `appointment_id`* (string)

### `clinical_observations`

Observations of the imported CDA record (Mon espace santé).

Paramètres : `search` (string | null, défaut `None`), `limit` (integer, défaut `50`), `offset` (integer, défaut `0`)

## Journal : pipi et repas

### `log_urination`

Record one urination (now, or ``at`` ISO date-time with offset).

Paramètres : `at` (string | null, défaut `None`)

### `list_urinations`

A day's urinations (default today): count and times.

Paramètres : `day` (string | null, défaut `None`)

### `delete_urination`

Delete one urination entry.

Paramètres : `entry_id`* (string)

### `log_meal`

Log a meal, then the AI reads it (minutes; poll get_meal).

meal_type: breakfast, lunch, snack or dinner (empty: from the hour
it was eaten). The description is
authoritative (quantities, cooking, no fat…); an optional photo helps
estimate portions. ``price``: what it cost (a delivery). Nutrients go
to Apple's nutrition metrics.

Paramètres : `description`* (string), `meal_type` (string, défaut ``), `eaten_at` (string | null, défaut `None`), `photo_base64` (string | null, défaut `None`), `photo_filename` (string, défaut `repas.jpg`), `price` (number | null, défaut `None`)

### `list_meals`

Meals with their reading (default: last 7 days).

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

### `get_meal`

One meal: foods, checked nutrients, score, verdict, remarks.

Paramètres : `meal_id`* (string)

### `update_meal`

Correct a meal (text, type, time); it is read again.

Paramètres : `meal_id`* (string), `description` (string | null, défaut `None`), `meal_type` (string | null, défaut `None`), `eaten_at` (string | null, défaut `None`)

### `analyze_meal`

Read a meal again with the current models.

Paramètres : `meal_id`* (string)

### `delete_meal`

Delete a meal, its photo and its nutrients.

Paramètres : `meal_id`* (string)

## Travail : heures d'embauche et de débauche

### `clock_in`

Clock in: start of work (now, or ``at``: ISO date-time).

A second clock-in while already at work is ignored. A time without
an offset is the user's local time.

Paramètres : `at` (string | null, défaut `None`)

### `clock_out`

Clock out: end of work (now, or ``at``); closes the open session.

Paramètres : `at` (string | null, défaut `None`)

### `work_sessions`

Work sessions between two days (default: last 30), newest first.

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

### `save_work_session`

Add a work session, or fix one (``session_id``).

Times are ISO date-times (local time without an offset); one of the
two may be missing (completed later). Overlaps and sessions over
72 h are refused. Confirm with the user before fixing.

Paramètres : `start_at` (string | null, défaut `None`), `end_at` (string | null, défaut `None`), `note` (string, défaut ``), `session_id` (string | null, défaut `None`)

### `work_incomplete`

Days to complete: sessions with a clock-in or clock-out missing.

Each comes with its context to help the user choose a time: the
day's proofs and traces (taxi, parking, receipts; the next morning
too for a missing clock-out), wake-up and bedtime, first and last
steps, the usual time for that weekday and overall. Suggest, never
decide: once the user picks a time, fix it with save_work_session
(``session_id``) and a note saying where the time comes from.

### `delete_work_session`

Delete one work session (ask the user first).

Paramètres : `session_id`* (string)

### `work_stats`

Hours worked: totals, averages, overtime, weeks, months, periods.

Default: the last 365 days. Overtime is per week beyond the contract;
flags: days over 10 h, weeks over 48 h (French legal maximums).
``periods`` gives 7 days / 30 days / 3 months / 1 year.

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`), `contract_hours` (number, défaut `35`)

### `import_work_log`

Import past clock-in / clock-out logs (txt, csv or json text).

First call with dry_run=true: it shows what it read (sessions, hours,
skipped lines); import for real (dry_run=false) once the user agrees.
Importing twice is harmless (same start = same session).

Paramètres : `text`* (string), `filename` (string, défaut `pointage.csv`), `dry_run` (boolean, défaut `True`)

### `export_work`

Work hours as text: level sessions / days / weeks / months, csv or json.

For a PDF use generate_report(report_type="work").

Paramètres : `level` (string, défaut `days`), `export_format` (string, défaut `csv`), `start` (string | null, défaut `None`), `end` (string | null, défaut `None`), `contract_hours` (number, défaut `35`)

## Dossier travail et santé : historiques, arrêts, preuves, nuits

### `import_logs`

Import iPhone Shortcut history files (one time stamp per line).

``files``: [{"filename": "Embauche.txt", "text": "...", "key": ""}].
The key comes from the file name when empty: work.start (Embauche),
work.end (Débauche), habit.cigarettes, habit.coffee,
water.bottles_1_5, elimination.urination. Send clock-in and clock-out
files together so they are paired. First call with dry_run=true, show
the user what was read, import for real once they agree.

Paramètres : `files`* (array), `dry_run` (boolean, défaut `True`)

### `list_absences`

Absences (sick leave, work accident…) with their cause.

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

### `save_absence`

Record (or replace, with ``absence_id``) an absence.

kind: arret_maladie, accident_travail, maladie_pro, conge or autre.

Paramètres : `start_date`* (string), `end_date`* (string), `kind` (string, défaut `arret_maladie`), `cause` (string, défaut ``), `note` (string, défaut ``), `absence_id` (string | null, défaut `None`)

### `delete_absence`

Delete an absence (ask the user first).

Paramètres : `absence_id`* (string)

### `list_evidence`

Proofs and traces between two local days, with their SHA-256.

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`)

### `add_evidence`

Add a proof or a trace: when, kind, how many, what it shows.

Proofs: appel, sms, mail, capture, note, document, autre. Traces
(a third party saw you): transport, taxi, parking, livraison, repas,
hotel, frais. ``trace``: {"ended_at", "place", "amount", "currency",
"meal": true} — "meal" logs a delivery / meal bought as a meal with
its price (AI-read). ``file``: {"base64", "filename", "media_type"}.

Paramètres : `occurred_at`* (string), `kind` (string, défaut `capture`), `title` (string, défaut ``), `description` (string, défaut ``), `count` (integer, défaut `1`), `trace` (object | null, défaut `None`), `file` (object | null, défaut `None`)

### `import_traces`

Import app exports and receipts as traces (Uber, Navigo, parking).

``files``: [{"filename": "trips_data.csv", "text": "...", "kind":
"auto"}] — or "base64" instead of "text" for a PDF / photo receipt.
kind: auto (guessed from a type column or the receipt), transport,
taxi, parking, livraison, repas, hotel or frais. A receipt and the
expense-report line of the same ride (same day, same amount) become
one trace. ``meals`` logs deliveries as priced meals. Dry run first,
then import for real once the user agrees.

Paramètres : `files`* (array), `meals` (boolean, défaut `True`), `dry_run` (boolean, défaut `True`)

### `delete_evidence`

Delete one evidence item and its file (ask the user first).

Paramètres : `item_id`* (string)

### `sleep_nights`

Nights by wake-up day, newest first: asleep, awakenings, blocks.

Default: every night since the first one known. Days without any
sleep data are listed as missing (watch not worn) unless
``missing`` is false.

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`), `missing` (boolean, défaut `True`)

### `add_sleep_night`

Type a night the watch missed (ISO local times; confirm first).

Paramètres : `bedtime`* (string), `wake_time`* (string), `awakenings` (integer | null, défaut `None`)

### `work_health`

The work ↔ health file: work, legal landmarks, sleep, absences.

Correlations (hours worked vs sleep the night after), nights after
days off / short / long days, weeks, months, years, absences with the
work and calls inside them, evidence. ``with_days`` adds every day.
For the PDF: generate_report(report_type="work_health").

Paramètres : `start` (string | null, défaut `None`), `end` (string | null, défaut `None`), `contract_hours` (number, défaut `35`), `with_days` (boolean, défaut `False`)

## Évolution, photos, données Apple

### `metabolic_markers`

Validated markers with their bands and inputs.

FibroScan CAP / E, WHtR, BMI, FLI, FIB-4, HbA1c, fasting glucose,
TyG: value, band, inputs used, dates and history.

### `evolution_trend`

Weight follow-up and long-term photo scores.

Weight: latest, changes over 1/3/12 months, loss from the 12-month
peak vs the 5/7/10/15 % milestones. Photos: scores per angle.

### `save_profile`

Record waist, height, birth year or a FibroScan (CAP dB/m, E kPa).

Paramètres : `waist_cm` (number | null, défaut `None`), `height_cm` (number | null, défaut `None`), `birth_year` (integer | null, défaut `None`), `cap_db_m` (number | null, défaut `None`), `lsm_kpa` (number | null, défaut `None`), `date_key` (string | null, défaut `None`)

### `list_photos`

Progress photos (face / profil / dos) with status and date.

Paramètres : `angle` (string | null, défaut `None`)

### `photo_analysis`

A photo's analysis: quality control, scores, paired comparisons.

Paramètres : `photo_id`* (string)

### `analyze_photo`

Re-run the photo method on one photo (vision model).

Paramètres : `photo_id`* (string)

### `reanalyze_all_photos`

Re-run the photo method on the whole history (after a model change).

### `list_workouts`

Workouts imported from Apple Health.

Paramètres : `limit` (integer, défaut `100`), `offset` (integer, défaut `0`)

### `list_ecg`

ECG recordings imported from Apple Health.

### `list_routes`

GPS routes (workouts) imported from Apple Health.

### `list_imports`

Apple Health import jobs with their status and counts.

## Rapports, automatisations, accès direct

### `generate_report`

Generate a report, then poll get_report.

Types: synthesis (AI clinical synthesis + clinical PDF, takes
minutes), clinical_pdf, work (hours worked PDF: totals, overtime,
weeks, months; default last 365 days), work_health (the work ↔
health file: work, legal landmarks, sleep correlations, absences,
day-by-day journal, evidence annex), csv, json, xlsx, fhir.

Paramètres : `report_type` (string, défaut `synthesis`), `period_start` (string | null, défaut `None`), `period_end` (string | null, défaut `None`)

### `list_reports`

Recent reports with their status (and synthesis when present).

### `get_report`

One report, with its AI synthesis when present.

Each kept sentence cites the numbered facts of the record; the
rejected sentences are listed with the reason.

Paramètres : `report_id`* (string)

### `list_automations`

The user's automations (NFC, shortcut, schedule…).

### `create_automation`

Create an automation (trigger: nfc/shortcut/manual/schedule/api).

Paramètres : `name`* (string), `trigger`* (string), `action`* (object)

### `run_automation`

Run an automation now.

Paramètres : `automation_id`* (string)

### `api_get`

Read any API route not covered by a tool.

E.g. /metrics/body.weight or /events; ``path`` is relative to
/api/v1 (see /openapi.json).

Paramètres : `path`* (string), `params` (object | null, défaut `None`)

### `api_call`

Call any API route (POST/PUT/PATCH/DELETE) not covered.

Destructive routes act on real health data: confirm with the user.

Paramètres : `method`* (string), `path`* (string), `body` (object | null, défaut `None`), `params` (object | null, défaut `None`)
