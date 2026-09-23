# Outils du serveur MCP

Généré depuis le serveur (`python -m phoenix_mcp.doc`) — ne pas éditer à
la main. Chaque outil appelle l'API REST avec le jeton `hub:full` ;
configuration et connexion d'un client : [guide MCP](guides/mcp.md).
Paramètre suivi de `*` : obligatoire ; sinon la valeur par défaut est
indiquée.

53 outils.

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

### `record_measurement`

Record one value (weight, cigarettes, symptom…); idempotent per day.

Paramètres : `metric_key`* (string), `value`* (any), `date_key` (string | null, défaut `None`)

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
minutes), clinical_pdf, csv, json, xlsx, fhir.

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
