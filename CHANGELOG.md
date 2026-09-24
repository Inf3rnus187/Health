# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Updates are the administrator's**: `/system/update` (state and
  « Installer ») needs an admin session (`AdminDep`, role `admin`); other
  users only get « Nouvelle version installée : recharge la page ». A
  waiting update is no longer hidden behind the green « ✓ installée »
  of the previous one, and the host looks at GitHub every 5 minutes
  (was 15).
- **Meal photos on a phone**: a square thumbnail, centred, instead of a
  tall photo stuck to the left; a tap shows it whole, a tap closes it.
- **« Mise à jour en cours » for ever after « Installer »**: `run/` is
  sticky (`1777`) and often owned by root or Docker, so the host's cron
  user could not delete the request dropped by the API (another user):
  `rm` failed every minute and the update never ran. `update.sh` now
  keeps a copy (`run/update-taken`) to mark it taken; each request is
  unique. The banner says where the host is, with the time (asked,
  running since, « ✓ … installée à … »), turns red with the log command,
  « Relancer la mise à jour » and « Masquer » when a request is not
  taken within 3 minutes or an update gives no news for 20 minutes; an
  update stopped midway is written « failed », never left « running ».
  The page also looks for the new build every 20 s while the host
  updates. `update.sh` is read whole before it runs (a pull may rewrite
  it).
- **The version loaded** is shown next to the name: « v20c48fe · 24/09
  20:52 » (commit and build time; `update.sh` / `install.sh` pass the
  commit to the web image).
- **A meal photo from the gallery**: on a phone the Journal's photo field
  opened the camera only. It now offers « 📷 Prendre une photo » and
  « 🖼️ Galerie », shows the photo picked and lets it be taken back.
- **A meal Shortcut without photo was refused (422)**: an empty `file`
  field (an iPhone Shortcut's « Sans photo » branch) now counts as
  absent. `eaten_at` also takes `23/09/2026 20:30` (day first, local
  time) besides ISO; a photo sent as `application/octet-stream` is still
  read (the decoder decides). The guide gives the whole Shortcut,
  yesterday's meal included.
- **A health meal is not an expense**: a meal logged in the Journal (web,
  Shortcut `POST /meals`, MCP `log_meal`) is the health follow-up only —
  it takes no price and is never a work proof. A meal paid for (receipt,
  delivery, expense report) is a proof added in Travail (`POST /evidence`,
  `meal=true`), which logs its meal in the Journal too, shown there as
  « 🧾 Note de frais ».
- **Santé's vital signs showed « Mesure indisponible »** for everyone
  with a tracker blocker: EasyPrivacy (uBlock, AdGuard, Brave, Safari
  blockers) drops every browser request under `/api/v1/metrics`. The
  web app reads a metric's overview at `/catalog/{key}/overview` (the
  `/metrics` path stays for scripts and MCP), like the catalogue
  already did; an eslint rule keeps web calls off `/metrics`. The
  tableaux de bord and « Une mesure en détail » had the same fault.
- **Phone header and menu**: one slim sticky line (name, theme, « ☰
  page »); « ☰ » opens a grid of every page with the account and
  sign-out — no sideways scrolling. Tabs wrap instead of scrolling.
- **Long lists are paged**: « Tout ce qui est enregistré » (Données),
  séances / ECG / tracés GPS (Santé), résultats d'examens, chronologie
  (with a type filter, e.g. without appointments) and documents (with a
  search) in the Dossier, now split in tabs (Synthèse, Chronologie,
  Documents, Imagerie, Importer); appointments « À venir » / « Passés »
  with a search in Suivi.
- A local day's bounds are bound in UTC (SQLite dropped the zone: a
  count logged between midnight and 02:00 in Paris was left out of its
  day in tests).

- **Every page uses the whole screen.** The content was held in a
  960 px column in the middle; it now spans the window, with a side
  margin that follows its size (12 to 32 px). The « À compléter »
  calendar follows the room it has: 6 months per row on a wide screen,
  then 4, 3, 2 (one below 300 px); its days grow with their month, the
  green dot of a complete day sits under the number instead of on it,
  and the day's card stays beside the months (under the menu, not
  behind it) — on a phone it moves under them and comes into view when
  a day is touched. On a phone the menu is one line that scrolls, tab
  labels no longer break, rows of buttons wrap, and nothing makes the
  page scroll sideways (the health dashboards, the import and nights
  forms did). A lone field keeps a readable width, a period's name
  stays on one line in tables, and the proof viewer opens wider.
- **A clocking can be undone where it was made**: the « Travail —
  aujourd'hui » card lists today's clockings with « Supprimer ». The
  Sessions card is tidied: « + Ajouter une session » opens a framed form
  (labelled times, « Lieu » instead of a loose checkbox) apart from the
  list; the period and filter sit on their own band; the table has
  column titles and says « sur place » / « à distance ». A period kept
  from an earlier visit that ends before today says so, with « Jusqu'à
  aujourd'hui ».
- **Periods, tabs and filters survive a reload.** Each card's period
  (Mes journées, Sessions, Statistiques, Preuves et traces, Nuits, the
  file's summary, Repas, Rapports), the tab open (Travail, Photos,
  dashboards by domain) and the filters (days, sessions, days to
  complete, proof kind and search, export level, report type) are kept
  in this browser. A period that ran up to today (« 30 j », « Tout »)
  moves on with the days; a past one stays as it was.
- **A page left open no longer ends on « 401 » / « identifiants
  invalides ».** The 15-minute access token was never renewed: every
  call then failed until a reload. The web app now renews it every 12
  minutes while the tab is visible and on the first 401 (once for all
  the calls waiting at the same time, another tab's renewal taken into
  account) and replays the call; files, uploads and imports go through
  the same path. A session that cannot be renewed any more leads to the
  login page, which says « Session expirée : reconnecte-toi ».

### Added

- **Mes aliments** (Journal › Mes aliments, `/foods`, MCP `list_foods`,
  `save_food`, `read_food_label`, `add_food_photo`, `delete_food`): the
  boxes and sachets eaten often, a sheet filled once — name, brand,
  other names used in meals, package weight, values per 100 g (salt as
  printed, stored as sodium), note, photos of the box and of its
  nutrition table. « Photo des valeurs (lecture IA) » reads the label
  and pre-fills the sheet (plausible values only) to check and save.
  Each food is its user's own (every query filters on the owner; anyone
  else gets 404, also when attaching it to a meal).
- **A meal computed from its label**: the foods picked in the meal form
  (with the grams eaten) and those its description names (their name or
  one of their other names, accents ignored) are given to the text model
  as authoritative label values; each is then recomputed by code from
  its label for the grams eaten (else the estimate, else the package
  weight), marked « étiquette 🏷️ » — no more « vérifier la composition
  du sachet ». The model's `food_id` survives the plausibility check.
- **Several photos per meal** (up to 7: the plate, then the box, the
  sachet, the nutrition table): « Galerie » picks several at once, each
  preview has its ×; the vision model sees them together and reads the
  labels. `POST /meals` takes `photos` (repeated) and `foods` (JSON);
  `POST/GET/DELETE /meals/{id}/photos[/{photo_id}]`; `MealOut` has
  `photo_ids` and `foods`; the extra photos (2048 px, cleaned,
  encrypted) show as thumbnails on the meal card. Migration `0017`.
- **« Refaire ce repas »**: a past meal fills the form again (type,
  description, foods of the list).
- **Journal in tabs**: Aujourd'hui, Repas, Mes aliments (the last one
  opened is kept).
- **What Uber Eats cost** (Travail › Statistiques › « Dépenses repas »):
  over a period, for deliveries (the imported Uber Eats orders), meals
  paid for (receipts) or both — total, orders, average basket, monthly
  average, largest order, late orders (21:00 – 05:00); spending per day,
  week or month (empty periods included); orders per hour of the day;
  the establishments that cost the most (`GET /spending/meals`, MCP
  `meal_spending`). Chart colours validated for colour-blind readers in
  light and dark; tables headers get their padding back site-wide.
- **A real daily journal** (Journal page). « Aujourd'hui »: last night
  (asleep, in how many goes, awakenings, bedtime → wake-up) and a tile
  per counter — water (1.5 L bottles, in litres), coffees, cigarettes,
  pees — with « +1 » / « − » (the Shortcuts' `/sync/tally`); the pee
  times under them. « Mon journal »: one line per day (night, water,
  coffee, cigarettes, pee, meals with their energy), a period, the
  page's averages, paged server-side (`GET /journal/days`, only the
  page's days are read; MCP `journal_days`). On a phone each day is a
  card.
- **Appointments deleted many at once** (`POST /appointments/delete`,
  MCP `delete_many("appointments")`): an agenda imported whole brings
  hundreds of personal events.
- **« À compléter » as a 12-month calendar** (default view; « Liste »
  keeps the cards one under the other): a pastille per day to complete
  (red without proof, orange with one) and the count per month, a green
  dot for a complete day, grey for an absence or a public holiday;
  clicking a day opens its card on the right (the same card), with
  « Jour précédent / suivant ». View, months shown and day picked
  survive a reload.

- **Update notice and `./update.sh`.** The page compares its build with
  the one installed (`/version.json`, written at each web build; nginx
  revalidates it and `index.html`) and offers « Recharger » after an
  update. `./update.sh` replaces the manual `git pull && docker compose up
  -d --build …`: fast-forward pull only (local changes stop it, nothing
  overwritten), rebuilds only the parts changed (api + worker, web, mcp if
  running; docs only: nothing), writes its status to `run/`. With
  `./update.sh --install-cron`, the host checks GitHub hourly and the page
  shows « Mise à jour disponible » (changes, parts to rebuild) with
  « Installer »: the API only drops a request file in `run/` (mounted at
  `/data/update`), the host's cron runs the update — no Docker socket in
  any container. `GET`/`POST /system/update`.

- **« Réunir » from a session's editor.** The sessions the typed times
  overlap show live, with their note, and « Réunir : 02/04 12:01 →
  03/04 21:22 » makes one session of both, keeping the times typed
  (`POST /work/sessions/{id}/merge` takes `start_at` / `end_at`): a
  33 h 21 continuous session can be entered over an existing one. A
  session ending another day shows that day in the list.
- **« Journées les plus significatives »** in the work ↔ health report
  (and `highlights` in `/work/health`): up to 20 days, the most striking
  first — continuous sessions of 24 h or more, amplitude over 13 h, more
  than 10 h worked, Saturdays, Sundays and public holidays worked, work
  during an absence, late ends — with arrival, departure (« +1 »),
  amplitude and the notes typed that day. Report tables now wrap long
  cells and keep their colours after a chart; « +2 » after two days.

- **Add a proof after the fact, where it is missing**: « + Ajouter une
  preuve pour ce jour » on each day to complete, in « Mes journées »
  (the « + » of the Preuves column, or under the proofs unfolded) and in
  a session's editor; « + Ajouter une preuve à cette absence » on each
  absence (linked to it). The same form as « Preuves et traces », dated
  that day. WhatsApp calls answered (« Appel vocal 3 min ») count in the
  day's activity until they end; the « Appel » proof gives their count,
  the missed ones and the total length.

- **WhatsApp chats as proofs** (`.txt` export, iPhone or Android, any
  date order, messages on several lines): per day, your messages are an
  « Activité pro » trace from the first to the last one you sent
  (presence, late traces, days to complete, evidence during sick
  leave); a day of messages received only is an « SMS / message »
  proof; calls are an « Appel » proof with their count; each lists the
  day's messages. The `.txt` is kept untouched as a document. You are
  « Moi » / « Me »… or the name chosen in the preview. Days of tickets
  and of each chat now merge per source (a chat never replaces the
  tickets of the same day).

- **Overlaps no longer block a day to complete.** Each card lists the
  day's other sessions (« 09:02 → ? — embauche seule »); « Réunir :
  09:02 → 19:12 » makes a lone clock-in and a lone clock-out one session
  (`POST /work/sessions/{id}/merge`, MCP `merge_work_sessions`; same
  place, the note keeps what the other held); a session completed
  around a lone clock-in or clock-out of the same place takes it in; a
  whole session before or after offers its end or start as the limit.
  The overlap error names the session (« Chevauche la session du
  02/03/2026 09:02 → 12:30 : … »).

- **Delete many items at once**: proofs and traces, work sessions,
  absences and Journal meals. Tick items or « Tout sélectionner » (every
  item the period and filters show, all pages), then « Supprimer la
  sélection (N) » after a confirmation; an item ticked then hidden by a
  filter is kept. Deleting delivery traces can take their Journal meals
  too; the days of deleted sessions are rebuilt. The proofs list also
  filters by words (title, place, detail, file name). API:
  `POST /evidence/delete` (`meals`), `/work/sessions/delete`,
  `/absences/delete`, `/meals/delete` — only the user's own ids go;
  MCP `delete_many`.

- **Uber rides and Uber Eats orders read from Uber's own export**
  (`rider_lifetime_trips`, `user_orders`), column by column:
  - a ride: pickup → drop-off at the exact time (the `_utc` columns; the
    `_local` ones carry a false « Z »), the pickup and destination
    addresses as Uber wrote them, request time, km, duration, the price
    paid (the price shown at booking, discount taken off), the tip
    apart, business profile, GPS points. Cancelled or unserved requests
    are listed, not imported;
  - an Eats order: the establishment, order and delivery times, the
    items with their options, the order price; the meal logged takes
    the delivery time;
  - the city column (the Uber account's zone, « Paris » for an order
    60 km away) is never taken for the place;
  - the import preview shows the first traces as they will be stored
    and why each left-out line was left out.

- **« Mes journées »: one line per day**, the Travail page's first tab:
  the night before (asleep, awakenings), wake-up, first clock-in, last
  clock-out, hours worked (remote part), bedtime, absence (½ for a half
  day), the day's proofs (unfolded, « Voir » / « Télécharger ») and the
  state (« à compléter » leads to the tab). Period, filter, paging,
  totals. `GET /work/days`, MCP `work_days`. The Travail page is split
  into tabs: Journées, À compléter (with its count), Sessions,
  Statistiques, Dossier travail et santé, Importer.

- **See a proof before choosing a time, and fix any correction.**
  - Each day to complete is a clear card: what is known, the day's
    proofs and traces in a table (and the morning after), landmarks, the
    time kept. « Voir » opens a proof over the page: its receipt or
    invoice (PDF, also in a tab), screenshot, place, amount and details;
    also from the proofs list.
  - « Corrigées à la main » lists every session completed or changed
    afterwards; « Modifier » (also on each session row) reopens its
    times, place and note with the day's proofs; clearing a time sends
    the day back to complete. Any later time change now marks a session
    `edited` (typed ones too). Deletions ask for confirmation.
  - Session list filter: fixed by hand, remote, incomplete.
- **Half days off** (migration 0016): an absence starts in the morning or
  the afternoon and ends at noon or in the evening; half days count ½
  in the days off, the week's target and the reports, and working the
  other half is not work during an absence. Absences can be edited.
  HR imports read half days (« après-midi » / « matin » columns or
  cells, one record per half day). MCP `save_absence` takes
  `start_half` / `end_half`.

- **Remote work.** A work session is on site or remote (migration 0015).
  A remote session can be added or clocked (« Embauche à distance »,
  Shortcut key `work.remote_start`, MCP `clock_in(remote=True)`,
  `save_work_session(remote=True)`) even on a day already worked on
  site; it counts as work time (hours, clock-out, legal landmarks) and
  apart in the new daily value `work.remote_hours`. A remote clock-in
  while an on-site session is still open starts its own session. Stats
  show the remote hours, days and days worked remote on top of the
  site; the weekly chart stacks the remote part; exports, the hours PDF
  and the work ↔ health file show it too.

- **Days off in the hours worked.** Sick leave (and work accident,
  occupational disease), holidays, rest days, other absences and public
  holidays now count in the work stats, the export, the hours PDF and the
  work ↔ health file: days off per kind (calendar and working days),
  days worked during an absence, a weekly average over full weeks only,
  each week's target reduced by its days off with the hours beyond it,
  weeks entirely off listed, and short / long-term averages per week
  present (days before the first record left out). Chart: orange weeks
  of sick leave, grey weeks of leave / rest / public holiday, the
  reduced target dashed. Legal overtime is unchanged (hours worked
  beyond the contract).

- **HR and tool exports.**
  - Lucca expense-report PDFs (the sealed archive or the printed report)
    give one trace per expense: day, nature, supplier, amount, amount
    paid in another currency, and the comment. The PDF is kept untouched
    as a document, so its seal stays verifiable. Lines met again (an
    Uber ride, the other layout of the same report) are merged and
    complete each other.
  - Ticket exports (NinjaOne…) give the chosen person's actions: one
    « Activité pro » trace a day, from the first to the last action,
    each action listed without the comment text. They count as attested
    activity on unclocked days, as late traces by their last action, and
    as hints for days to complete.
  - `POST /absences/import` reads an HR export (Lucca…: CSV, Excel,
    JSON): start and end days, or one day per record joined across
    weekends; the kind (congés payés → congés, RTT → new « repos » kind,
    maladie → arrêt maladie…); refused, cancelled and remote-work rows
    are skipped; pending rows are noted; a manager's export keeps one
    person; nothing is added twice.
  - Web: an « Importer des absences » card, and the person choice for
    tickets. MCP: `import_absences`, and `import_traces` takes `person`.

- **Exact periods and pages everywhere.** Hours worked, sessions, the
  work ↔ health summary, proofs and traces, nights, meals and reports
  share one period picker: 7 d / 30 d / 3 months / 1 year / all, plus
  exact « Du … au … » days; reports keep and show their period, and the
  report list now offers the work ↔ health PDF. Long lists page with a
  « par page » selector (10 or more). Nights are no longer limited to
  the last 30 days (`/sleep/nights` defaults to the first night known,
  `missing=false` hides days without data); evidence periods are local
  days (a taxi at 00:30 belongs to that day).
- **Help to complete a day.** `GET /work/incomplete` lists every session
  with a missing half, newest first, with « preuve présente » and the
  day's context: proofs and traces (the next morning for a missing
  clock-out, stays covering the day), wake-up and bedtime, first and
  last steps, the usual time for that weekday and overall. The page
  shows them as clickable times, filters by proof, and saves a note on
  where the time comes from. MCP: `work_incomplete`; `sleep_nights`
  takes `missing`.
- **Date-time from the file name** when adding a proof or trace
  (`2026-05-09 03h47.pdf`, `09-05-2026_03.47.png`,
  `IMG_20260509-0347.jpg`): the same patterns as receipt imports.

- **Traces and expenses** in the work ↔ health file. Evidence also holds
  traces — what third parties recorded: transport, taxi / VTC, parking,
  delivered meal, meal bought, hotel, expense report — with an end time,
  a place and an amount (migration 0013). A delivery or a meal bought
  can be logged as a meal with its price and vendor, read by the AI;
  meals take a price. `/traces/import` reads Uber, Uber Eats, Navigo,
  parking, hotel, expense-report and bank exports (CSV, Excel, JSON) by
  their column titles: UTC times converted, cancelled rows skipped, the
  rows of one order merged, nothing imported twice. The report adds a
  « Traces et dépenses » section (presence attested on days never
  clocked, late traces, spending by kind and month, deliveries on long
  days with their AI score, hours vs meal spending) and the day's traces
  in the journal; days to complete show the day's traces. MCP:
  `add_evidence` takes a trace, `import_traces`, `log_meal` a price.

- **Work ↔ health file** (Travail › Dossier travail et santé), to support
  a sick-leave, work-accident or occupational-disease claim with facts:
  - sessions may miss a half (a departure logged alone, an arrival never
    closed): kept and listed in « Journées à compléter », completed by
    hand and marked `edited`; sessions up to 72 h (migration 0012);
  - absences (`/absences`): sick leave, work accident, occupational
    disease, holidays, with cause and notes;
  - evidence (`/evidence`): call, SMS, mail, screenshot, note, document,
    with a count, a file (encrypted at rest) and its SHA-256;
  - nights (`/sleep/nights`): per wake-up day, sleep, awakenings, blocks
    (sleep in several goes), bedtime / wake-up, best device kept; nights
    typed by hand when the watch was flat;
  - `/work/health` and report type `work_health`: sources and gaps,
    work summary, Code du travail landmarks (rest < 11 h, spread > 13 h,
    sessions ≥ 12 h, 12-week average > 44 h, Sundays, public holidays,
    night hours, consecutive days), work ↔ sleep correlations with a
    plain reading and night-after bands, years / months / weeks with
    sleep and health, absences with work and calls inside them, the
    day-by-day journal and an evidence annex (images, SHA-256);
  - `/logs/import`: iPhone Shortcut histories (`12 | 13/05/2025 07:42`),
    one kind per file guessed from its name; arrivals and departures
    paired without dropping anything, counters fill empty days (never
    doubled), pee de-duplicated;
  - ten MCP tools (81 in all).

- **Travail — work hours as health data.** Clock in / out by the same
  Shortcut rule as every count (`POST /sync/tally` with `work.start` /
  `work.end`, GPS automations welcome), from the new **Travail** page or
  by the assistant (`clock_in` / `clock_out`). Sessions (`/work/sessions`,
  table `work_sessions`, migration 0011) feed three daily metrics
  (`work.hours`, `work.start`, `work.end`) like any other data, and a home
  tile. Statistics (`/work/stats`): totals, averages, overtime per week
  beyond the contract (35 h, adjustable), days over 10 h and weeks over
  48 h (French legal maximums), weeks, months and 7 d / 30 d / 3 m / 1 y
  periods. Export per session / day / week / month in CSV, Excel or JSON
  (`/work/export`), PDF report type `work`. Import of past logs in txt,
  csv or json (`/work/import`, dry run first): French and English dates,
  embauche / débauche words, CSV headers, JSON records, night shifts;
  re-importing never duplicates. Eight MCP tools (71 in all).

- **Longitudinal photo method v2 (abdominal fat / liver / diabetes
  follow-up)**. Replaces the single-photo free-text analysis, which could
  not measure an evolution:
  - *Protocol* shown in the Photos page (morning, fasting, same place /
    light / distance, relaxed belly; waist tape measured weekly per WHO).
  - *Deterministic quality control* (brightness, Laplacian sharpness,
    resolution): unusable photos get status `low_quality`, are never sent
    to the AI and never enter the statistics.
  - *Blinded rating* per angle on anchored 0–10 scales (face: waist width,
    belly volume; profil: belly protrusion, lower-belly sagging; dos: love
    handles, back rolls). Ollama runs greedy with a fixed seed, so a
    re-analysis is reproducible.
  - *Paired comparisons* vs the baseline (first good photo) and the ~7 /
    30 / 90-day photos: both images in one labelled picture, order never
    revealed, asked twice with the order swapped to cancel position bias;
    non-mirrored answers are flagged "peu fiable".
  - *Long-term statistics* (`GET /evolution/trend`): daily median, 7-day
    rolling median, Theil–Sen slope over 90 days, change vs baseline; a
    trend is only reported with ≥ 8 days over ≥ 21 days.
  - *Validated markers* (`GET /evolution/markers`): WHtR, BMI, Fatty Liver
    Index, FIB-4 (age-adjusted), HbA1c, fasting glucose, TyG, with their
    published bands, freshness date and missing inputs; waist / height /
    birth year entered in the web form (`POST /evolution/profile`).
  - `POST /evolution/reanalyze-all` re-runs the method over the whole
    history (Ollama calls serialised so long runs don't time out).
  - *Weight follow-up* in the Évolution view: every weigh-in (Apple Health,
    Health Auto Export, web form) → latest, 7-day median, 12-month curve,
    Theil–Sen slope, changes over 1 / 3 / 12 months, loss from the
    12-month peak vs the 5 / 7 / 10 % (EASL MASLD) and 15 % (DiRECT)
    milestones; each before/after photo shows that day's weight.
  - Each marker lists the exact values (and dates) used by its formula.

- **One truth for every page.** One metric key per concept whatever the
  channel (SpO2, HRV, breathing rate, flights, distance, waist, weight,
  glucose had two keys), units converted at write time; `POST
  /data/reconcile` (run automatically after each Apple import) merges a
  user's duplicate keys and recomputes every daily value from the raw
  samples with a single rule — one HealthKit channel per day (native
  export and Health Auto Export carry the same data: never added, a
  partial day never overwrites a full one), explicit entries kept. This
  also restores days an interrupted import never wrote.
- **Données page**: "Tout ce qui est enregistré" (every metric, raw and
  daily counts per source with their period, reconcile button) and
  "Valeurs journalières (toutes sources)".
- **FibroScan** (CAP, stiffness E) in the web form and read from reports;
  markers graded S0-S3 / F, FLI and FIB-4 flagged as superseded.
- **Marker history** from previous lab results.
- **AI reading of medical documents** (document model, e.g. MedGemma
  1.5), with every AI value grounded in the document text.
- **One Ollama model per task** (`OLLAMA_VISION_MODEL`,
  `OLLAMA_DOCUMENT_MODEL`, `OLLAMA_TEXT_MODEL`); the photo trend only
  mixes scores of the current vision model.
- **Complete Apple Health catalog (HealthKit SDK, iOS 26)**: all 121
  quantity and 72 category types have a French label, a Health-app domain,
  a unit and a daily rule, so a full Apple export, Health Auto Export and
  lab / document imports write the *same* metric for the same concept.
  Category events (symptoms with their severity, stand hours, heart-rate
  notifications, mindfulness minutes, cycle tracking…) now get a numeric
  value and chart like any other metric.
- **Health Auto Export names**: every spelling the app has used maps to
  the HealthKit type (e.g. `walking_running_distance`, previously stored
  under a stray `apple.*` key); blood pressure is split into systolic /
  diastolic, `sleep_analysis` into its sleep stages; its percentages
  (already 0-100) are never scaled twice.
- **Reconcile** also aligns stored data with the catalog (labels,
  domains, numeric category events, HAE percentages) and folds the old
  stray keys into their canonical metric. It does not call any AI model.
- **A real medical record (Dossier)** built from the documents
  (`GET /medical/record`): diagnoses and medications the AI read in
  reports and prescriptions but not yet declared are offered for
  confirmation (never added silently; each links its documents); every
  lab / FibroScan result with its latest and previous value, change,
  history and the document it was read from; one chronology of
  documents, diagnoses, treatment starts / stops and appointments.
- **Suivi by condition** (`GET /care/overview`): each declared condition
  with the indicators that follow it (e.g. hepatic steatosis → CAP,
  stiffness, ALAT / ASAT / GGT, triglycerides, weight, waist; diabetes →
  HbA1c, fasting glucose…; smoking → cigarettes, breath, SpO2), their
  latest value, change and curve, and the documents mentioning it.
- **AI clinical synthesis report** (report type `synthesis`): the whole
  record becomes numbered facts (conditions, treatments, markers with
  their bands, lab / FibroScan results with their previous value,
  weight changes and loss from peak, key Apple Health indicators over
  the last 30 days vs the 30 before and a year ago, photo trend,
  documents); the text model (e.g. MedGemma 27B) writes the synthesis,
  evolutions, points of attention, items to discuss and missing data,
  citing a fact for every sentence. A sentence without a reference, or
  with a number or code (S3, HbA1c…) absent from the facts it cites, is
  removed and listed with the reason. Shown on the Rapports page (hover
  a reference to read the fact) and at the top of the clinical PDF, with
  the facts in an annex. A model failure is reported, never hidden.
- **MCP server covers the whole hub** (62 tools): data and metrics
  (overview, samples, trends, inventory, reconcile, entries), the record
  (Dossier, Suivi, documents and the text the AI read, conditions,
  treatments, appointments, CDA), markers, weight / photo evolution,
  Apple workouts / ECG / routes, reports with the AI synthesis,
  automations, plus `api_get` / `api_call` for any other route.
- **`hub:full` token scope** (« Accès complet — MCP / assistant »): lets
  a token do everything the web app does; managing tokens, 2FA, the
  account and the Shortcut download still require an interactive login.
- MCP `streamable-http` transport (now the compose default) answers each
  request with plain JSON and needs no session, so a single `curl` can
  list the tools or call one.
- **Journal** page: what Apple Health does not record.
  - *Pee log*: one tap (web or iPhone Shortcut with `?token=`) = one timed
    entry; the daily count (`elimination.urination`) is a metric like any
    other (charts, Suivi for diabetes / sleep apnoea, reports).
  - *Meals*: type (breakfast, lunch, snack, dinner), time, description and
    an optional photo (EXIF / GPS removed). The AI reads them: foods and
    portions (vision model, the description takes precedence), nutrients
    per food and an assessment for the declared conditions (text model:
    score 0–10, verdict, positives, points to watch). Impossible foods are
    dropped with the reason and energy is recomputed from the macros. The
    totals go into Apple's nutrition metrics as `meal` samples; editing,
    re-reading or deleting a meal replaces or removes exactly them.
  - API `/journal/urination`, `/meals`; 9 new MCP tools (62 in all).
- `GET /medical/documents/{id}/text`: the text the AI reads from a
  document (OCR for scans), to check an extraction against its source.
- **Documentation** (French guides): configuration (every variable, tokens
  and scopes, services, logs, updating), page-by-page usage and common
  tasks, medical AI (models per task, document reading and rejected
  values, clinical synthesis, photo method, troubleshooting), MCP (safe
  setup, Claude Desktop / Claude Code / stdio); Health Auto Export in the
  ingestion guide. **Generated references**: `docs/api.md` (every route,
  its parameters and required access, read from the code) and
  `docs/mcp-tools.md` (every MCP tool and its parameters); tests fail when
  either is out of date.
- `GET /catalog/domains`: French name of every domain, used by the
  dashboard tabs (Apple Santé and the hub's own domains — tabac, PPC,
  biologie…).

### Fixed

- Work documents downloaded instead of opening: like medical documents,
  « Voir » now opens every proof and trace file and every PDF report in
  a new tab (a blob, the type guessed from the name when the server
  sends none), with « Télécharger » beside it; « Détails » shows what
  was read.
- Exporting sessions failed on a session whose clock-in is missing.
- CSV files whose quoted cells contain doubled quotes (a ticket comment)
  were split into wrong rows: doubled quotes are now always read as one.
- « Au travail depuis » and the disabled « Embauche maintenant » came
  from any clock-in never closed, even weeks old: only a session opened
  less than 16 h ago is open now.
- **Receipts and expense reports reconciled.** Importing a PDF receipt as
  a trace failed with a 500 (it was read as a CSV); receipts and
  invoices (PDF, scanned PDF, photo — OCR) are now read: day, time (from
  the file name, as Uber names its receipts, or the text), total paid,
  who billed it, items and invoice number, the file kept with its
  SHA-256. A receipt and the expense-report line of the same ride (same
  kind, day and amount; times equal or one unknown) are one trace,
  completed in either order (migration 0014: `time_known`). Expense
  reports: a column naming each line's kind wins over the file's kind,
  untitled and unknown columns are kept in the description, "du … au …"
  gives a stay's exact start and end, and a stay of 6 h or more marks
  presence on each day it covers. An unreadable file is reported, never
  a crash. Days to complete offer the day's traces (and the next
  morning's) as one-click times.
- **Home tiles for pee and distance walked.** « Pipi » (count of the day,
  time of the last one) and « Distance marche/course » (km of the day)
  sit on the home page with cigarettes and coffee; a count prints bare
  (« 5 », not « 5 count »).
- **Backend tests: ~30 s instead of tens of minutes.** Without Redis,
  every queued job (import, AI reading, report) waited ~5 s of arq
  reconnections; tests now fail a queueing at once. The database is
  seeded once per run and copied for each test instead of re-seeded
  200 times.
- **One rule for every iPhone Shortcut.** A pee needed its own route
  (`/journal/urination`) while a bottle, a coffee or a cigarette went
  through `/sync/tally`. Now every one-tap count uses `POST /sync/tally`
  with `{"metric": "<key>"}` — `elimination.urination` included (each pee
  is kept with its time, `-1` takes the last one back). A meal (text +
  photo) is the only other path, `POST /meals` with the same token; its
  type defaults to the hour instead of always « Déjeuner ». The usage
  guide has one « Raccourcis iPhone » section with the keys.
  `/journal/urination` still works (the Journal page uses it).
- **The MCP could erase a count.** « Ajoute une clope » went through
  `record_measurement`, which *replaces* the day's value: the total was
  overwritten (1, then 11). Now:
  - new MCP tool **`add_to_counter`** (`POST /sync/tally`) adds to the
    day's total and never erases it; a negative amount takes back a
    wrong entry, never below 0; it returns the total before and after;
  - `record_measurement` refuses to replace a different value unless
    `replace=true`, passed only after the user confirmed, and returns
    the value it replaced; the server instructions say so;
  - `/sync/tally` counts on the user's local day (was the server's UTC
    day) and answers `previous` with `total`;
  - every overwrite is recoverable: `POST /measurements` logs the values
    it replaces in the audit log (`replaced`), each tally step logs the
    total before and after.
- Home tiles showed raw sample units (lb, SpO2 fraction) and ignored a
  newer typed weigh-in; QuickWeight used the UTC date and refreshed
  nothing.
- Health Auto Export recomputed a day from its payload only (partial
  days overwrote full ones).
- Markers never found imported lab values: the blood-test import stores
  them as `bio.<analyte>` but the markers looked up bare keys. Both now
  use one shared key helper, and a test imports a real lab PDF end to end.
- Merging duplicate keys renamed a shared metric definition when its
  canonical metric was missing (a unique-key failure when two old keys
  shared one target). The canonical metric is now created from its spec
  and the old rows folded into it; a manual entry or a query on an old key
  (`stairs.floors`, `sleep.spo2_avg`…) reads and writes the canonical one.
- A lab value imported today for an older blood test was shown as
  measured today, and could even hide newer Apple weigh-ins; a value is
  now dated by its measurement day everywhere, and shown without a
  made-up time when only the day is known.
- PDF reports printed "?" for œ, typographic quotes or dashes; domain
  titles now use the shared French names.
- MCP `get_measurements` / `get_daily_summary` sent `from` / `to` where
  the API expects `start` / `end` (the period was ignored), and three
  tools called routes that no longer exist.

### Security

- **API tokens need `read:all` to read health data.** The scope was never
  checked: any token — including the write-only one embedded in the
  iPhone Shortcut or the CSV token — could read the export, the values,
  samples, summary, markers, photos, reports, Apple records and the CDA
  record. These routes now answer 403 without `read:all` (sessions and
  `hub:full` tokens are unaffected). Existing tokens used only to send
  data keep working; a token that must read needs `read:all` added.
- A token without `read:all` can no longer create reports, and deleting
  all photos, deleting or re-analysing one photo, re-analysing the photo
  history and resetting the Apple import now need a login or `hub:full`
  (previously any token, for photos, or a `write:measurements` token,
  for the reset).
- The MCP server no longer holds a shared token anyone on the network
  could use: each client sends its own `hub:full` API token (checked with
  `GET /auth/scopes`, 401 / 403 otherwise, cached one minute) and the
  tools call the API with it — one token created in the web app, nothing
  secret in `.env`, each user sees only their data, revoking the token
  cuts the access. Compose publishes the port on 127.0.0.1 unless
  `MCP_BIND` says otherwise.

### Changed

- `PHOTO_PROMPT_VERSION` is gone: the method version is part of the code
  (`v2`) and only v2 analyses feed the statistics. Older v1 analyses stay
  readable. The `ai.silhouette_change` text metric is no longer written.

- **Photo AI failure no longer marks the photo broken**: the pipeline now
  stores/normalises the image and analyses it in two isolated steps. If
  Ollama is unreachable the photo stays viewable with status `ai_failed`
  ("IA indisponible") instead of the whole photo showing `error`; `error`
  is reserved for an image that genuinely can't be decoded.
- **Home tiles show the current reading**: an instant metric's tile (heart
  rate, SpO2, HRV, respiratory rate, weight…) now shows the **latest raw
  sample's value and its real time**, instead of the day's average stamped
  with the last sample time — which made a live reading look like "2 hours
  ago". Cumulative metrics (steps, energy, water) keep showing the daily
  total. The sparkline still reflects the daily history.
- **Clinical PDF for a doctor**: the report was a bare list of raw metric
  keys with a single average. It now has a **Faits marquants** recap, an
  **Évolution des indicateurs clés** section with per-metric **trend
  line-charts** (drawn as vectors — no chart dependency: weight, HR,
  resting HR, HRV, SpO2, respiratory rate, sleep, steps), and per-domain
  tables (Corps, Coeur, Sommeil, Activite…) showing the human label + unit
  and latest / average / min / max / count. Generation date in the header;
  all text latin-1-sanitised so an unusual label never crashes the render.
- **Faster imports**: the shared importer now commits once per ~50k rows
  (bulk-inserting every 5k) instead of committing every batch, so a
  full native export writes far fewer fsync-bound transactions; timestamp
  parsing is hand-rolled for the canonical Apple format (~3.4× faster than
  `strptime`, and it's called twice per sample); and each HealthKit type's
  metric spec is resolved once and cached. Applies to both the XML and CSV
  paths.

### Added

- **Delete photos**: a "Supprimer" button on each photo (`DELETE
  /photos/{id}`) and a "Tout supprimer" button on the Photos tab (`DELETE
  /photos`) remove the row, its analyses and the on-disk files.
- **Re-run a photo analysis**: `POST /photos/{id}/analyze` and a "Relancer
  l'analyse" button re-queue the normalize + AI pipeline for an existing
  photo (e.g. one stuck from an earlier Ollama outage), without
  re-uploading.
- **HEIC/HEIF photo support**: Apple devices (and mirror cameras) capture
  HEIC, which PIL and web browsers cannot read — so an uploaded HEIC showed
  as a black "IMAGE ILLISIBLE" tile even though the file was fine. The
  normalizer now registers `pillow-heif`, decodes HEIC/HEIF and re-encodes a
  browser-safe JPEG, and intake accepts `image/heic` / `image/heif`.
  Verified end to end (HEIC upload → normalized → served as an image).
- **Photos tab**: a new "Photos" page shows the progress photos uploaded via
  `POST /ingest/photo` (mirror/device) as a grid — angle (Face/Profil/Dos)
  filter, date, linked weight, processing status, and the **AI (Ollama
  vision) analysis** per photo. Images are fetched with the auth token
  (blob) since the file endpoint is owner-only. Previously the photo
  pipeline had no viewer at all — photos could be uploaded but not seen.
- **Token manager in the web UI**: the Import tab gets a *Jetons d'accès*
  card to create an API token and **tick its scopes** (Photos
  `ingest:photo`, Montre/Santé `ingest:watch`, Mesures `write:measurements`,
  PPC, métriques, lecture seule), see each token's scopes and revoke — so a
  non-technical user can mint the right token (e.g. the `ingest:photo` token
  a photo mirror needs) without curl. The one-off secret is shown once with
  a copy button; the CLI path stays available. Previously the UI could only
  mint a fixed `write:measurements` token, which is why photo uploads 403'd
  with "Missing scope: ingest:photo".
- **Health Auto Export (JSON)**: `POST /sync/auto-export` ingests the JSON
  body posted by the *Health Auto Export* iOS app
  (`{"data":{"metrics":[{"name,units,data:[{date,qty}]}]}}`) — no multipart
  file, unlike the CSV upload. Metric names map to the matching HealthKit
  identifier so they land on the same canonical keys a native export uses
  (and are auto-created when missing); each point is recorded on its own
  date, `qty` or `Avg` taken as the value. Same `write:measurements` token
  (`?token=` in the URL), so the app needs no header. A full history export
  is tens of MB and tens of thousands of points, so the payload is chunked
  (the ingest schema caps a batch at 500) and timestamps are parsed
  timezone-aware (PostgreSQL rejects naive ones); nginx lifts its 25 MB
  body cap on this route. Like the native Apple import, every point is now
  stored as a raw `health_samples` row (so it appears in the **Données**
  browser, not only as a daily tile) **and** folded into a daily
  `measurements` roll-up via the shared `DailyAggregator` — summed for
  steps / distance / energy / exercise minutes, averaged for heart rate /
  SpO2 — so a daily tile is a real total, not the last minute's reading.
  Units are normalised (e.g. SpO2 0.96 → 96 %). Re-pushing a day replaces
  that day's Health-Auto-Export samples, so the every-5-minutes automation
  stays idempotent instead of piling up duplicates.
- **One-tap counters (café, cigarette, eau)**: `POST /sync/tally` adds to a
  metric's *daily total* (read-modify-write) instead of overwriting it, so
  an iPhone Shortcut can tap `{"metric":"habit.cigarettes"}` repeatedly and
  the day's count climbs. Body is `{metric, amount?=1, date_key?}`; the
  token rides in the URL (`?token=`) so no header is needed. Fractional
  amounts work (a half mug of coffee = `amount: 0.5`), and the seeded
  `water.bottles_1_5` feeds the derived `hydration.liters` (× 1.5). Reuses
  the same `write:measurements` token as the CSV upload URL.
- **Biologie → valeurs suivies**: `POST /biology/import` parses a
  **text-based French lab PDF** (pypdf) and records each analyte's current
  value **and its antériorités** (previous value + its own date) as
  measurements under `bio.<key>` metrics — so a blood test becomes real
  tracked curves. Parsing is **catalog-driven** (`biology_catalog`): only
  recognized analytes are recorded, with canonical labels/units, so notes,
  method lines, thresholds and continuation lines (e.g. `soit (IFCC)`)
  never become fake metrics. It handles the real report layouts — name on
  its own line, `percentage then absolute` counts (records the absolute),
  the same analyte in two units, French thousands separators — and matched
  a full BIOGROUP hémogramme + biochimie + bilan on the real PDF: **45
  analyses, 85 values across 4 dates** with zero junk. `DELETE
  /biology/values` (and a "Réinitialiser la biologie" button) purges all
  `bio.*` values and their now-empty metrics to recover from a bad import.
  The source PDF is kept as a `biologie` document. Dossier tab gets an
  "Analyser une prise de sang (PDF)" upload.
- **OCR for scanned PDFs**: a scanned (image-only) lab PDF has no text
  layer, so biology import now falls back to **OCR** (`ocr` service:
  PyMuPDF rasterises each page, Tesseract reads it in French) and feeds the
  result through the same strict catalog — a scanned blood test still
  yields tracked values, and OCR noise cannot create junk metrics because
  unrecognised lines are simply skipped (verified: a fully rasterised
  BIOGROUP report still yields 27 analyses / 50 values, zero junk).
  Tesseract (`tesseract-ocr` + `tesseract-ocr-fra`) is added to the backend
  image; when it is absent the import degrades gracefully (the document is
  still kept). Note: OCR can drop decimal points on dense EFR / blood-gas
  tables, so structured EFR / gaz-du-sang value tracking is intentionally
  not auto-recorded yet — those reports are kept as documents.
- **Visionneuse DICOM**: the Dossier tab gets a built-in DICOM viewer
  (`components/dicom`, using `dicom-parser`) to open the `.dcm` files from
  an imaging CD (scanner, IRM, radio) — entirely in the browser, nothing is
  uploaded. It renders uncompressed monochrome studies (8/16-bit, signed or
  not, little- or big-endian, MONOCHROME1 inverted, rescale slope/intercept
  applied) with window-centre/width controls (auto-fit from the pixel
  range) and a slice slider for a multi-file series, plus a metadata panel
  (patient, modality, study/series, dimensions). Compressed transfer
  syntaxes (JPEG/JPEG2000) are detected and reported with their metadata
  rather than rendered — a full codec stack can come later.
- **Dossier CDA du médecin**: `POST /clinical/import` imports a
  doctor-delivered **French CI-SIS / HL7 CDA** file (namespace-agnostic
  parser reused from the native-export clinical path). Each `<observation>`
  becomes a searchable clinical observation (label / value / unit / date)
  browsable in Santé → Observations cliniques, and the raw CDA is stored
  encrypted as a `cda` document. The Dossier tab gets an "Importer un
  dossier CDA (médecin)" upload.
- **Caregiver report (tout donner au médecin)**: the clinical PDF now also
  prints the care record — Maladies, Traitements, Rendez-vous and a
  Documents médicaux index — right after the recap, so the single exported
  report hands a doctor the metrics *and* the medical history in one file.
- **Suivi médical (conditions, treatments, appointments)**: a new "Suivi"
  tab and APIs to declare maladies (`/conditions`), traitements
  (`/treatments`, with an active toggle) and rendez-vous (`/appointments`),
  including **Apple Calendar (.ics) import** (`POST /appointments/import`,
  deduped by UID) parsed with a dependency-free VEVENT reader. Tables added
  via migration `0007`.
- **Dossier médical (medical documents)**: a new "Dossier" tab and API
  (`/medical/documents`) to upload, list, view and delete medical files —
  ordonnances, imageries + comptes-rendus, biologie (prises de sang), EFR,
  tests de marche, dossier CDA, vaccinations, autre. Files are stored
  encrypted at rest (same crypto layer as photos), typed and dated, and
  purged by RGPD account erasure. Table added via migration `0006`.
- **Home = a health hub**: each `/summary` tile now carries `at` (the
  newest raw sample time), `delta` (day-over-day change), `avg7` (7-day
  average) and `spark` (last 14 daily values). The Accueil tiles show the
  reading time, an evolution arrow, a sparkline and the 7-day average, and
  sleep renders as hours (`6 h 28`). Added HRV and respiratory rate to the
  headline set.
- **Santé tab no longer blank**: it now leads with a **Signes vitaux —
  tendances** section (heart rate, resting HR, HRV, SpO2, respiratory rate,
  sleep charts) so a CSV-only import (no workouts/ECG/routes) still shows
  content, plus a hint explaining those records come from the native Health
  export.
- **iPhone CSV sync**: the Apple Health import (`POST /imports/apple-health`)
  now **auto-detects** and ingests a **SimpleHealthExportCSV** zip (one CSV
  per HealthKit type) in addition to Apple's native `export.xml` — same
  full-fidelity `health_samples` storage, daily roll-ups and on-the-fly
  `apple.*` metric creation. This is the reliable device path since iOS
  refuses to import unsigned shortcut files (server-side signing is
  impossible). The Import → « Synchro iPhone » card now mints a
  `write:measurements` upload token and shows the exact POST config for the
  shortcut's upload step. The upload also accepts the token as a `?token=`
  query param (not just the `Authorization` header), so the shortcut needs
  only a URL — no fragile header entry on mobile. The CSV parser tolerates
  the real export's quirks (Excel `sep=,` preamble, UTF-8 BOM, CRLF), maps
  the short sleep-stage values (`asleepCore`/`asleepREM`/…) into the sleep
  roll-ups, and routes `HKWorkoutActivityType…` CSVs into the workouts
  table (duration/energy/distance) rather than generic `apple.*` samples.

- **iPhone one-tap sync**: Import → « Synchro iPhone » now offers a
  **pre-filled downloadable Shortcut** (`GET /sync/shortcut`) with the
  scoped token and endpoint already embedded — no data picking, no JSON
  editing. It posts to `POST /sync/health`, a Shortcut-friendly flat
  `{date_key?, metrics:{type:value}}` map with lenient numeric parsing
  (`"86,2 kg"`, `"8 542 pas"`). The manual copy/paste recipe and its dead
  helper components were removed.

### Changed

- **Robust ingestion**: a `healthkit_type` with no user mapping now
  resolves via the Apple spec and **auto-creates** its metric
  (`MetricCache`), so `/ingest/watch` and `/sync/health` no longer drop
  unmapped types — they land under `apple.*` (matching the zip importer).
  Previously such samples were reported as `skipped`.

- **Hardening (Phase 9)**: optional **TOTP MFA** (`/auth/mfa/*`; login
  requires `otp` when enabled), optional **at‑rest media encryption**
  (Fernet, transparent via `app.core.crypto`), and **RGPD erasure**
  (`DELETE /me` cascades all data and purges media/export files). Added a
  `Security` CI workflow (gitleaks, pip‑audit, pnpm audit, Trivy fs, syft
  SBOM) and a gitleaks pre‑commit hook. Migration `0003` adds the MFA
  columns idempotently (ADR‑0004/0005).
- **Automations (Phase 8)**: CRUD for trigger→action rules
  (`/automations`, triggers nfc/shortcut/manual/schedule/api) plus
  `POST /automations/{id}/run` which executes the action — `reminder`
  (returns the message) or `capture` (opens a capture session). Exposed as
  MCP tools `list_automations`/`create_automation`.
- **MCP server (Phase 7)**: a FastMCP server (`mcp/`) exposing hub tools —
  `list_metrics`, `create_metric`, `record_measurement`, `get_measurements`,
  `get_trend`, `get_daily_summary`, `get_photo_analysis`, `compare_photos`,
  `generate_report`, `export_data` — each a thin client of the REST API
  (single source of truth), authenticated with a scoped token. Runnable via
  the `mcp` compose profile; its own lint/type/test CI job.
- **Exports & reports (Phase 6)**: `GET /export?format=csv|json|xlsx|fhir`
  streams a tidy dataset (`date, metric_key, value, unit, source`); the FHIR
  format emits an R4 `Bundle` of `Observation` resources. `POST /reports`
  generates a report (clinical **PDF**, or any export format) as an async
  worker job with an inline fallback when no worker is running;
  `GET /reports/{id}` reports status and `GET /reports/{id}/file` streams the
  result to its owner. Adds `openpyxl` and `fpdf2`.
- **Dashboards (Phase 5)**: `GET /dashboard/{domain}` returns every numeric
  metric of a domain as a rolling series (using each metric's aggregation
  hint). The React app gains a domain tab bar and a dashboard grid that
  renders each series through the single governed chart component.
- **Photo pipeline (Phase 4)**: `POST /ingest/photo` (multipart, scope
  `ingest:photo`) stores the original outside the web root, EXIF‑sanitizes
  and normalizes it (Pillow), then queues an async worker job that runs the
  Ollama vision model for a strict‑JSON silhouette analysis, links the
  previous same‑angle photo for comparison, and injects the AI change as a
  measurement (`source=ai`). Read via `GET /photos`, `/photos/{id}`,
  `/photos/{id}/analysis`, `/photos/compare`, and the authenticated
  `/photos/{id}/file` stream. Ollama URL/models are configurable and mocked
  in tests.
- **Ingestion (Phase 3)**: `POST /ingest/watch` and `POST /ingest/ppc`
  accept generic samples keyed by `metric_key` or by an external
  `healthkit_type`, resolved through a **configurable mapping table**
  (`ingest_mappings`) so new fields are absorbed with no code change;
  unresolved keys are reported, not fatal.
- Mapping management: `GET/POST /ingest/mappings`; seeded global HealthKit
  defaults.
- **Mode B** `POST /capture`: opens a `capture_session` event, records
  weight + photo flags, pre‑fills the latest Watch/CPAP data and returns the
  manual‑only complement form.
- Alembic migration `0002_ingest_mappings` (incremental, per‑table from the
  ORM metadata).

## [0.1.0] — 2026-01

Foundation milestone (specification Phases 1–2).

### Added

- Docker Compose stack: `db` (PostgreSQL 16), `redis`, `api` (FastAPI),
  `worker` (ARQ), `web` (Nginx + React build), optional `mcp`.
- One‑shot `install.sh` bootstrap (build, migrate, seed, admin) and a fully
  commented `.env.example`.
- Authentication: argon2id passwords, JWT access tokens, **rotating and
  revocable** refresh sessions, `/auth/{login,refresh,logout,me}`.
- Scoped, hashed **API tokens** with CRUD and scope enforcement.
- **Dynamic metric registry** (`/metrics`) — add a field at runtime with no
  migration.
- **Measurements**: idempotent batch write, filtered reads, rolling
  aggregation series; **events** with attached measurements.
- Polymorphic typed measurement storage; partial unique indexes for zero
  redundancy; derived metrics marked read‑only.
- Seeded metric **catalogue** (Annexe A, 76 metrics) + initial admin.
- Append‑only **audit log** of every write.
- Alembic initial migration driven by the ORM metadata.
- React (Vite + TS) front: login, token/auth flow (TanStack Query), metric
  catalogue, a governed chart component with a semantic palette, quick weight
  entry.
- Quality tooling: ruff, mypy (strict), ESLint + Prettier, a custom
  structural‑limits checker, pre‑commit config, and GitHub Actions CI with a
  ≥ 80 % coverage gate.
- Documentation: README, architecture and data‑model docs (Mermaid), how‑to
  guides, and ADRs.

### Security

- Security headers + strict CSP (web tier), restricted CORS, non‑root
  hardened container images.

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/v0.1.0
