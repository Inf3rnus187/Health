# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Several accounts reconciled at once no longer multiply processes and
  database connections** (for the administrator of a hub with several
  users). The worker runs up to 10 jobs at once (`WORKER_MAX_JOBS`): 10
  accounts importing together would each have started
  `RECONCILE_PARALLEL` processes, 40 more connections near PostgreSQL's
  100. One reconcile at a time now has processes in a worker; the others
  wait their turn, holding no transaction meanwhile. The total time is
  the same (the work is processor-bound), the load is bounded. A test
  reconciles two accounts at once: never two sets of processes, both
  accounts' days right (it fails without the lock).

- **The web page's settings are public, and hold nothing private**:
  `GET /system/settings` (read before signing in) gives only timings and
  form limits from the environment — no secret, nothing of an account.
- **A request may now be 32 MB through nginx** (`WEB_MAX_BODY_MB`, was a
  fixed 25): a proof of up to 30 MB (`EVIDENCE_MAX_MB`) was refused by
  nginx before the API that accepts it. The API's own limits still
  apply to each file.

- **Compressed answers never carry a secret**: nginx gzips text but
  not sign-in, session renewal, API tokens nor a Shortcut with its token
  (BREACH).
- **Health data sent to the hub no longer lands on nginx's disk**: the
  bodies of `/api/` requests (meal photos, documents, Health Auto
  Export's JSON…) were written unencrypted to a temporary file of the
  `web` container before reaching the API (« a client request body is
  buffered to a temporary file » in its log); they are now streamed to
  the API as they arrive. Checked through nginx: a 7.9 MB meal photo, a
  650 KB Health Auto Export JSON (also sent chunked) arrive whole, no
  warning, and a body over 25 MB is still refused (413).
- **The API's access line names the client nginx saw** (`X-Real-IP`, an
  address of your network) instead of nginx's container; tokens in URLs
  are still written `token=***`.
- **The iPhone app's token goes in the header only**: `POST` and `GET
  /sync/healthkit` take a `write:measurements` token from the
  `Authorization` header and refuse `?token=`; they reach only the
  owner's `healthkit` rows (UUIDs are unique per user) and each sync is
  audited with its counts.
- **Explanation links send nothing**: the links of « Comprendre ces
  références » (EU, ANSES, WHO, Santé.fr, Open Food Facts, Ciqual) are
  plain links the browser opens in a new tab only when tapped, without
  a referrer; the hub itself calls nothing and the addresses carry no
  data (a product link carries its barcode only).
- **Nightly Open Food Facts re-reading**: with the lookup on, the
  worker sends each sheet's barcode again when its page is older than
  `FOOD_REFRESH_DAYS` (default 30; 0 turns it off) — the barcode only,
  50 a night at most.
- **`POST /stock` accepts `?token=`** (an iPhone Shortcut scanning
  groceries): like the other Shortcut routes, the token needs
  `write:measurements` only and is written `token=***` in the logs; it
  can only add to the stock of the token owner's own foods.
- **No token in the logs**: an iPhone Shortcut sends its API token in the
  URL (`?token=…`); the API's access log and nginx's now write
  `token=***` (the token stays valid, it just never lands in a log file).
- **The MCP never sends a token elsewhere**: `api_get` / `api_call` (and
  every tool) accept only API paths (`/metrics`, relative to `/api/v1`);
  a full URL, `//host`, `..` or a backslash is refused before any
  request.
- **The metric catalogue is the administrator's**: creating or changing
  a metric (unit, bounds, « active ») changes everybody's data, so
  `POST /metrics` and `PATCH /metrics/{key}` need the `admin` role
  (session, or an admin's `write:metrics` token); reading is unchanged.

### Fixed

- **Three settings were missing from `.env.example`** (for the
  administrator): `UPDATE_DIR`, `GIT_COMMIT` (leave it unset:
  `./update.sh` gives it) and `REDIS_URL` (set by compose; only outside
  Docker). They were in the configuration guide, but the test checking
  the example covered only the tuning values: it now covers every
  setting the API reads, so a new one cannot be left out. The check
  that a code change comes with its CHANGELOG and docs now also watches
  `version.sh`. Found by an audit of the 33 commits since 30 September
  (each with its CHANGELOG and a hand-written doc; the generated API and
  MCP references up to date at each; one measurement, « pages no longer
  wait behind a photo », written in `docs/performance.md` one commit
  later than its change).

- **A reconcile started by a script given on Python's input no longer
  fails** (for the administrator: `docker compose exec worker python -
  <<EOF …`). The parallel reconcile's first version started its
  processes with `multiprocessing` (`spawn`), which makes each one
  re-read the main script: « <stdin> » is no file, the processes died
  and the reconcile stopped (`BrokenProcessPool`). The worker itself,
  started by `arq`, was not affected. Each process is now a program of
  its own (`python -m app.cli.rollup_worker`), fed one metric at a
  time, whatever started the reconcile; a process that fails stops the
  others at once (the metric each was on is not committed). Same times
  and the same days, same md5, on the test data; a test covers the
  script case. Measured at the user's, quietly, twice each: 1 process
  17.7 and 18.7 s, 4 processes 9.5 and 9.5 s, with 56–59 % of the
  processor still free and no disk wait to speak of (the 13.8 s just
  after the update ran while the containers restarted);
  docs/performance.md gives the command, which measures 1 against 4
  processes and what the machine does meanwhile.
- **A day's value no longer changes in its last digit from one
  recompute to the next** (for everyone). PostgreSQL starts reading a
  large table where the previous read of it stopped, so the samples of
  a big metric came in a different order after another read had been
  interrupted, and a sum could differ at its 13th digit (1 243,55 kcal
  stored as 1243.550000000001 or 1243.5500000000009: 4 or 5 days out
  of 44 016 on the test data, invisible on the pages). A recompute now
  always reads from the table's start: same order, same sums, however
  many recomputes run at once.
- **The slow pages left are fast, nothing left out** (same fake data,
  old and new code side by side over HTTP, all 71 GET routes compared:
  identical answers; see [docs/performance.md](docs/performance.md)):
  Données' inventory 364 → 23 ms (the raw samples' counts are kept by
  the database, table `sample_counts`, exact at every write: an import
  costs ≈ 1 % more, deleting 100 000 samples 1.45 s instead of 1.13 s);
  `/measurements` without a filter (an MCP call) 2 130 → 404 ms, from
  January 244 → 63 ms (read as columns, written in one pass; the order
  between two values of the same day and time, left to chance before,
  is now fixed by id); dashboards over the whole history 164–213 →
  61–82 ms (the objects an API process keeps for life are left out of
  Python's garbage collections, `GC_FREEZE`; large series written
  directly instead of being validated twice; the rolling window slides,
  same result to the last bit); stock 154 → 80 ms, « À compléter »
  291 → 181 ms; a full reconcile 16.3 → 11.9 s (conversions prepared once
  per unit, rows read without the ORM; the 37 238 computed days
  identical). The security headers are added without copying each
  answer.
- **A meal's AI remarks agree with its reference table** (for
  everyone): the table could say « protéines : au-dessus de la part du
  dîner » while a remark said « apport modéré ». The model now gets each
  nutrient's verdict before it writes, and a remark that calls a
  nutrient low, moderate or high against its verdict is replaced by the
  hub's sentence (« Protéines 36 g : au-dessus de la part d'un dîner
  (15–20 g). »); in the one-line verdict only the wrong part is cut.
  Snacks have no part, nothing to follow. `reference.rows` also gives
  the meal's `value`.
- **A proof of 25 to 30 MB is accepted**: nginx stopped it at 25 MB
  (413) while the API allows 30; nginx now takes 32 MB by default.
- **The work reports write the rules in force**: « Jours de plus de
  10 h », « semaines de plus de 48 h », « Heures de nuit (21 h - 6 h) »,
  the Code du travail landmarks and « fin après 21 h » follow the
  settings instead of fixed text.

- **The site no longer stays on « Le hub ne répond pas » after an
  update**: an update rebuilding the API alone gave its new container a
  new address; nginx kept the old one (« connect() failed (111:
  Connection refused) », 502 on every call) until `web` restarted. nginx
  now asks Docker's DNS again every 10 s: reproduced locally (still 502
  12 s after the API moved), fixed (back within 10 s).
- **Every route measured, the slow ones fixed** (5 years of fake data in
  every domain, old and new code side by side, answers identical; see
  [docs/performance.md](docs/performance.md)): « À compléter » 1 375 →
  293 ms, adherence 229 → 14 ms, `/facts` 289 → 34 ms, stock 427 →
  210 ms, home 110 → 68 ms (17 tiles read together: 5 queries instead of
  88), trends 28 → 12 ms, nights 43 → 28 ms, a full reconcile 56 → 19 s
  (samples read by blocks of 20 000, not one by one; the 44 016 daily
  values rebuilt identical).
- **The site loads faster on a phone**: nginx compresses text (nothing
  was: the page's code 1 047 → 308 KB, a dashboard's JSON 594 → 45 KB),
  each page's code is fetched when first opened (185 KB to open the home
  page instead of 1 047 KB), the libraries apart so an update reloads
  only the hub's own code. On a simulated 4G phone the login page shows
  in 0.58 s instead of 2.90 s. A page left open during an update reloads
  itself once when it opens a page whose code the update replaced, and
  otherwise says « Cette page n'a pas pu se charger » with « Recharger »
  (checked: a real build A → B while the page is open).
- **« Supprimer les données importées » says what stays**: its
  confirmation now names Health Auto Export and the iPhone app beside
  entries, counters, meals and documents (only the Apple export's rows
  go). Docs brought up to date: the iPhone app in the README, the
  architecture and the user guide (one Apple channel a day, time in bed
  merged across devices), `GET /nutrition/references` in the ingestion
  guide, the home tiles in the MCP guide, 114 MCP tools, what
  `LOG_JSON` changes.
- **Pages with years of Apple data load several times faster** (2.35
  million fake samples over 5 years, median of 3 calls, see
  [docs/performance.md](docs/performance.md)): Santé → Activité 1 274 →
  116 ms, Accueil 614 → 118 ms, Santé → Corps 580 → 80 ms, Santé → Cœur
  361 → 50 ms, Données « Tout ce qui est enregistré » 294 → 84 ms. Rolling
  averages read only their own window instead of the whole series for
  each day; a metric's view reads the days it shows (counts, first day
  and sources come from the database) instead of years of rows; a new
  index `(user_id, start_at)` on raw samples (migration `0025`, about 3 s
  to build on 2.35 million samples at the first start) lists every
  metric by date without sorting. Same numbers as before: every answer
  compared byte for byte.
- **Pages no longer wait behind a photo or a scan**: turning an iPhone
  photo into a JPEG (a meal's, a food's, a progress photo), reading a
  label or a barcode, and the OCR of documents, receipts and lab PDFs
  ran inside the API's process and froze it while they worked: with two
  processes, any page request landing on the busy one waited. While a
  meal with 3 large photos is received, the slowest small request took
  3 650 ms; it now takes 22 ms ([docs/performance.md](docs/performance.md)).
  That work runs in a thread; the API keeps answering.
- **An update no longer logs you out**: a page loaded while the API
  restarted (502) threw the session away; it now shows « Le hub ne
  répond pas (redémarrage après une mise à jour ?) — nouvel essai toutes
  les 5 s… » and comes back on its own, still signed in. Only a session
  the hub refuses goes back to the login page.
- **A night is the watch's**: the Nuits view kept, among the devices of
  a night, the one that saw the most sleep — another app counting more
  minutes than the watch won. The Apple Watch (which writes the phases;
  the iPhone only « in bed ») is now always kept when it recorded the
  night; another recorder counts only for a night the watch missed,
  never added to it.
- **Cigarettes, coffees and water show the time of the last one**: on
  the home page these tiles had a date only — a counter kept the time
  of its first addition, and a time was shown only when its UTC day was
  the counter's day. Each addition for the current day now dates the
  total, and a time is checked against the user's own time zone (a
  coffee at 01:30 in Paris is 23:30 UTC the day before); the water
  tile passes its time on too. An addition made afterwards for another
  day still shows its date only.
- **Grams written after « cuit », « nature » are read**: « 1 pavé
  saumon cuit nature 100g » was read as 1 pavé × 100 g (« comptés »)
  because the grams came 4 words after the food; « cuit », « nature »,
  « cru »… are now skipped, so written grams win (« 150g » would have
  given 100 g before).
- **« sel » and « sodium » now name what a remark quotes**: « Comté :
  sel (120,9 mg par 30g) » quoted the comté's sodium (403 mg/100 g ×
  30 g) as salt, which is 302 mg (sodium × 2,5). The check now reads
  the word the quantity belongs to (« 302 mg de sel », else the last
  « sel »/« sodium » before it in its sentence) and corrects it:
  « sodium (120,9 mg par 30g) », « 0,3 g de sodium » → « 0,3 g de
  sel ». Salt quoted in mg (« 302 mg de sel ») is now accepted, and the
  prompt says the « sodium » figure is sodium, not salt.
- **Meal cards no longer scroll sideways on a phone**: the four buttons
  (Modifier, Refaire ce repas, Réanalyser, Supprimer) stayed on one line
  and pushed the card 60 px past a 390 px screen; they now wrap.
- **A count you write beats what a photo shows**: with a photo, « 2
  tomates » became 50 g and « un demi concombre » 30 g — the grams the
  vision model saw of a small salad, which the text model kept. The code
  now reads the count said (« 2 », « un demi », « une tranche ») and
  multiplies it by the weight of ONE unit the model gives (`unit_g`,
  never the share on the photo); the line shows « 240 g = 2 × 120 g,
  unité estimée par l'IA ». Both prompts say the photo only serves what
  the description does not quantify.
- **« un filet de poulet cuit » found its reference**: the Ciqual list
  offered to the model was built word by word, and for « poulet » the
  references with « cuits » came first — « Poulet, manchons marinés,
  préemballés, rôtis/cuits au four » (12,6 g of fat, 674 mg of sodium
  per 100 g) was picked, while « Poulet, filet sans peau grillé/poêlé »
  (2 g, 56 mg) was not offered: a meal's sodium read 1 224 mg instead of
  about 600. Each part of the description now first offers the
  references naming all its food words, cooked ones first for « cuit »,
  generic before bio, label rouge, marinated or prepacked.
- **The header shows the version installed**: it showed the page's own
  build, so after an update of the server alone (« reconstruit : api »)
  it still read the older commit however often the page was reloaded.
  It now shows the host's last finished update and its time, the same
  as « ✓ À jour (…) » (`GET /system/version`, any signed-in user); the
  page's build is in the tip.
- **NOVA, percentages and added sugar checked in remarks**: the
  remarks called a NOVA 3 pack (« transformé ») « ultra-transformé »
  (that is NOVA 4), then « pas transformé »; « ne sont pas
  transformées » said of NOVA 3 or 4 is now corrected too, while « pas
  ultra-transformé », true of NOVA 3, is kept as written. The judgement prompt now says what each group
  means, and the code corrects « ultra-transformé » said of foods known
  to be NOVA 1 to 3; a percentage quoted must be in the named foods'
  ingredients or fruits-and-vegetables share (else its brackets are
  cut); « sucre ajouté » said of foods whose ingredients are known and
  hold no sugar drops the remark.
- **A number quoted belongs to what the remark talks about**: « grâce au
  saumon (24,6 g) » quoted the meal's protein as the salmon's (20,5 g):
  the check only asked that the number exist. It now asks that it be
  one of the values of the foods the remark names, or a meal total when
  it names none or speaks of the meal; otherwise its brackets are cut.
  Checks moved to `meal_remarks`. The model is told the same, one short
  sentence per remark, and to assume nothing of a composition beyond
  the ingredients given.
- **Remarks no longer cut mid-sentence**: they were truncated at 200
  characters (« Il est important de surveiller »); they now end at
  their last full sentence (300 characters), else at a word with « … ».
- **Remarks quote exact numbers**: the model wrote its remarks in the
  same answer as the grams, before the code computed the values, so it
  quoted its own arithmetic (« 557 mg pour 185 g » where the sheet gives
  562,4 mg; « 10.6 g » of sugars for 10,4). The reading now has two
  steps: the foods and grams first; then, from the values the code
  computed, the score, verdict and remarks, told to copy the numbers.
  The code then checks every quantity a remark quotes against the
  computed ones and cuts one that is not (its brackets, or the remark).
- **Fruits and vegetables %**: the sheet showed an older Open Food Facts
  field (81 % for a pack whose page says ~96 %); it now takes the one the
  page shows (« fruits, légumes, légumes secs », given, else estimated:
  « ~ »). « Tout relire » updates existing sheets.
- **Grams written are kept, and every line says where its grams come
  from**: grams written in the description (« tomates 240 g ») now
  replace the model's for every food, not only those of « Mes
  aliments »; each line of the analysis shows « écrits », « comptés »,
  « ta portion », « saisis », « le paquet » or « estimés par l'IA »
  (« 2 tomates » had become 400 g estimated after 200 g the time
  before, with nothing to tell).
- **Salt and sodium shown**: a sheet is filled with the salt printed on
  the pack and stored as sodium (1 g of salt = 400 mg), but nothing
  showed the sodium. The sheet now writes it under the salt field and
  the list shows « sel 0,76 g (sodium 304 mg) ».
- **Open Food Facts: nothing of the product page is dropped any
  more**: the lookup asked only for the name, brand, weight and 8
  values. A sheet now keeps everything the page gives (`product_info`,
  migration `0023`): ingredients, allergens and traces, additives,
  Nutri-Score, NOVA group, fruits and vegetables %, levels (salt,
  sugars, fat), labels, categories, serving, every other nutrient per
  100 g and the page's link; sodium is taken as given rather than
  recomputed from salt. The sheet shows a summary (« Nutri-Score B ·
  NOVA 3 · fruits et légumes 96 % ») and the details; the meal reading
  is given them as authoritative. Existing sheets: « Modifier » →
  « Code-barres » (code filled in) → « Chercher » → « Enregistrer ».
  MCP `lookup_barcode` returns them and `save_food` keeps them.
- **No « vérifier l'étiquette » on known values**: when a meal contains
  foods of « Mes aliments », a remark casting doubt on their label or
  composition is cut by code (the rest of the remark stays).
- **Your foods found by the words you use**: a meal named a food of
  « Mes aliments » only with every word of its name, so « un pavé de
  saumon » took the Ciqual table instead of « Saumon sauvage rose ». A
  word of the name now suffices when nothing else in that part of the
  description contradicts it and something confirms it (a box or
  sachet, the sheet's unit « pavé », its brand, or two words of its
  name); « filet de poulet » still does not take « Poulet basquaise »,
  and a part two sheets fit equally takes neither. « une boîte » without
  a number is one box (the sheet's package weight). The model's own
  line for such a food is replaced by the sheet, a second one dropped
  (no double count). « Réanalyser » a meal to apply it.
- **The MCP assistant logs meals as said**: its instructions and
  `log_meal` now ask it to call `list_foods` and pass the foods named,
  to keep the user's own words (the quantities are read in them), to
  leave the meal type empty unless it is said (5 h is a breakfast, not a
  snack) and to say which lines come from the user's sheets.
- **« Supprimer les données importées » asks first**: it erased every
  Apple export value at one click; it now asks for confirmation.
- **Report times in the page**: the list of reports showed the creation
  time in UTC (two hours early in summer); the API now sends it with its
  offset.
- **Counter taps say where they came from**: the audit log recorded the
  web page as « api » and every Shortcut as « token »; it now writes
  « web » / « raccourci » with the token's id (reports show « site » /
  « raccourci »).
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

- **The first sync after an update is no longer the slow one** (for
  everyone using the iPhone app). Each API process paid, on its first
  sync after a start, for its database connection, its first prepared
  statements and its code run once (212 ms at the user's, 32 ms the
  next one; 4 processes, so 4 such syncs per update). When a process
  starts (after the migrations, before it answers), it now opens one
  connection — the one its syncs then reuse — and runs a sync's
  **reads** once, for an account id no account can have, then rolls
  back: nothing written, no account's data read (tested: no write
  statement sent, every table keeps its rows, on SQLite and
  PostgreSQL). `API_WARMUP` (`true`); a failure is logged
  (`warmup_failed`) and the API starts anyway. Looking up a sample
  sent again no longer looks up (or makes) the sleep metric when none
  is stored. Bench (HTTP, fake data, 6 starts each): first sync after a
  start 176.5 → 127.5 ms (median; 140–197 → 111–150 ms), the next ones
  unchanged (88 / 86.5 ms); same fingerprints, counts exact. Cost:
  50–80 ms when each process starts. Method in
  [docs/performance.md](docs/performance.md).

- **A sync's trace shows Python's garbage collections, and new samples
  delete nothing** (for the administrator, and everyone syncing). At
  the user's, with the host's memory freed (266 → 110 ms a sync, no
  code changed), two steps stayed above the test bench: `validate`
  13 ms and `samples:forget` 33 ms. Measured on their hub (read-only):
  validating the same body takes 0.29 ms, the lookup by UUID 0.2 ms,
  and the `DELETE` that finds nothing 0.03 ms — but it still runs the
  count trigger, 5.7 ms. Now: (1) when none of the UUIDs sent is stored,
  no `DELETE` is sent (samples and workouts), so no trigger; (2) each
  sync's `ms` holds `gc`, the time the API process spent in garbage
  collections during the sync (a pause inside the other steps, not
  added to them), to see whether that is what remains. Bench (HTTP,
  fake data, 3 starts × 6 syncs, twice): `samples:forget` 4 → 1 ms,
  `samples` 9 → 7 ms (medians); totals within noise (86/78 before,
  91/84 ms after); same fingerprints, counts exact. A UUID sent again
  still replaces its sample (tested). At the user's afterwards: `gc`
  1–2 ms, so not the cause; a sync bringing nothing new takes 32 ms in
  all; the long steps were each API process's first sync after a
  restart (new connection, first prepared statements: 212 ms). Method
  in [docs/performance.md](docs/performance.md).

- **Removing a sample no longer reads the other sources' history**
  (for everyone; seen at the user's: `deleted` 59–80 ms and
  `samples:forget` 79–155 ms for one or a few UUIDs). When a delete
  removes the first or last sample of a count group (account, metric,
  source), the trigger keeping `sample_counts` exact reads that date
  again; the only index by date had no source, so the app's
  (`healthkit`) bound came only after every native-export sample of the
  same metric. A new index `ix_samples_group_start` (account, metric,
  source, date — migration `0031`) reads it in one step. Measured on
  fake data (370 000 heart-rate samples), a sync deleting the app's
  oldest heart-rate sample: 121–140 → 8–9 ms (10.7 s → 2.2 ms for the
  bare `DELETE` cold); its newest: 11–12 → 7 ms. Cost: built once at
  the API's start (≈ 10 s for 2.4 million samples, ≈ 2–3 s for 600 000;
  writes wait meanwhile); importing 315 000 fake samples 24.7–26.6 s
  before, 24.9–25.3 s after (no measurable cost); counts exact, same
  fingerprints. SQLite (tests) now reads samples in its rows' order
  when the table's order is asked, as PostgreSQL does: the new index
  had made it pick another order, so another channel on a tie. Method
  in [docs/performance.md](docs/performance.md).

- **A sync of the iPhone app no longer rewrites the sums it sends
  again unchanged** (for everyone using the app). At each sync the app
  sends today's hours again; only the hour still counting has changed.
  Each was deleted, written again and its day recomputed, type by type
  (6 deletions, 6 writes, every type's day). Now a sum stored exactly
  as sent (type, interval, value, unit) stays; the others are deleted
  and written in one statement each for all types, read in one
  statement too (one branch per type on the partial index), and only
  the days that changed are recomputed. The metrics of a sync are
  looked up once, in one query (20 lookups before); a sync without
  sleep or workouts no longer looks theirs up. « Dernière synchro »
  now also reads the sync's audit record (a sync that changes nothing
  writes no row). Measured over HTTP on fake data (2.4 million samples,
  3 starts × 6 syncs of 10 samples and 90–126 sums, twice): usual sync
  143–148 → 74–82 ms (median), first sync after a start 215–225 →
  141–170 ms; days and samples identical (same fingerprints), counts
  exact. New steps in the times: `samples:forget`, `samples:write`,
  `statistics:read`, `statistics:delete`, `statistics:write`. Method in
  [docs/performance.md](docs/performance.md).

- **`./version.sh`: which code runs, before reading any log** (for the
  administrator). One look at the host: the repository's commit (date,
  title), the commit the API and the worker were started with, the
  database's migration and the last update, then « ✓ L'API et le worker
  tournent avec le code serveur du dépôt » or « ⚠ … lancer
  ./update.sh ». An update of the docs or the page alone leaves the API
  on its older commit with the same server code: no false alarm. Put it
  in front of a diagnostic command (`./version.sh && docker compose
  logs api …`). It only reads.

- **A sync's time now counts from the request's arrival, and says which
  code ran.** Before the route: `receive` (the body from nginx), `json`
  (read as JSON), `token` (checked, with its database connection),
  `validate` (each field checked); `total` starts with the access line,
  so the access line minus `total` is only the answer being written.
  The log line and the audit record carry the `commit` running.

- **Every iPhone app sync says where its time went** (for the
  administrator, to find what to speed up — today or months later).
  Each `POST /sync/healthkit` times its steps: zone, deletions, samples,
  sums, workouts, nights, the days recomputed (all, and each metric:
  `days:heart.rate`…), the workouts' days, the commit and the total, in
  milliseconds. They go to the API log (`healthkit_synced`, with the
  counts) and to the account's audit log (`ms`; the commit is logged
  only, it comes after). The access line's duration minus `total` is
  the reading of the JSON and the token. No value, sample date or UUID
  is written. Cost measured: 1.05 µs per step, under 0.05 ms a sync;
  same answers (tests). Method in
  [docs/performance.md](docs/performance.md).

- **See from the hub whether the iPhone app's lines were all kept** (for
  everyone syncing with their own app). Each sync now records in the
  account's audit log the lines it refused (type, reason, count — never
  a value). Import › App iPhone shows them over the last 7 days
  (`SYNC_REFUSED_DAYS`): « ✓ Aucune ligne refusée sur 7 j (N synchros
  vérifiées) », or « ⚠ N lignes refusées » with each type, its reason
  (cumulative sent as a sample, discrete sent as a sum, unknown type…),
  how many and the last time. The app or a Shortcut reads the same in
  `GET /sync/healthkit` (`refused`, same token), and the assistant in
  `iphone_app_sync`. A sync received before this version did not record
  its refusals: it is not counted as checked. Tested: counts per type,
  old syncs apart, older than the window left out, another account's
  syncs never counted.

- **A reconcile uses several processor cores** (for everyone, and for
  the administrator: `RECONCILE_PARALLEL`, 4 by default). Recomputing a
  metric's days is Python work on one core; the metrics share nothing,
  so 4 are now recomputed at the same time, each in its own process
  with its own database connection, by the unchanged rule
  (`daily_rollup.rebuild`), the ones with the most samples first.
  Measured on the test machine (4 cores, 2.4 million fake samples, 21
  metrics, warm, median of 3, old code run in turn): 10.8 s → 5.4 s,
  then 9.7 s → 5.2 s in a second series (2 processes 6.3 s, 3 4.9 s:
  on 4 cores, 3 and 4 are alike, PostgreSQL needs a core too, and the
  largest metric sets the floor); the days written are
  identical, byte for byte, with 1, 2 or 4 processes (44 016 daily
  rows, same md5). Cost while it runs: about 85 MB and one connection
  per process (331 MB for 4); they stop with the reconcile. `1` runs
  the metrics one after the other, as before (measured: as fast as the
  old code, 10.6 and 9.7 s against 10.8 and 9.7 s).
- **A small sync from the iPhone app takes ≈ 0.1 s instead of 1–3.5 s**
  (for everyone using the app). Two causes, each per type of sum and
  per sync: the count trigger read back both dates of the `healthkit`
  group when a sync replaced its latest sums, the first one only after
  every older sample of the native export (160–180 ms warm, 12.6 s
  cold) — it now reads back only the removed date, a few ms (migration
  `0029`); and finding the stored sums a sync overlaps read the
  metric's history from 2021 (≈ 70 ms to find, as much to delete) — a
  partial index of the app's sums by their end finds them in a few rows
  (migration `0030`). Measured with syncs like the user's (111 sums,
  177 samples): 640–1 030 → 92–174 ms; days written identical, counts
  exact; the first full sync unchanged (≈ 10 s for 20 requests).
- **Imports and syncs write samples 3 to 10 times faster again** (for
  everyone). SQLAlchemy handed asyncpg the rows one at a time, so the
  trigger keeping `sample_counts` exact (added with the inventory
  speed-up above) ran once per row, updating the same count row again
  and again: importing 315 000 fake samples went from 25.8 s to
  198–218 s. The « ≈ 1 % » measured then inserted 5 000 rows per SQL
  statement, unlike the app; the regression was missed. Samples are now
  written with PostgreSQL's `COPY`, in one block, same transaction, same
  checks, column defaults filled as before: iPhone sync (samples, sums),
  Health Auto Export, Apple import. Import of 315 000 samples: 198–218 →
  21–23 s (better than before the trigger); 5 000 samples: 0.59–0.66 →
  0.19–0.22 s; an app's first sync of 20 requests: 24.0–27.6 → 11.6–
  12.3 s. Samples and days written identical; counts exact.
- **The iPhone app's first full sync no longer reads the whole history
  again at every request** (for everyone using the app). A first sync
  sends years of history in requests of at most 5 000 samples and 5 000
  sums; each recomputed every touched metric from its first day received
  up to today (a request of 2023 read 2023–2026 again, native export
  included). Each request now recomputes only the days it changes, from
  the first to the last, read in the table's order as the reconcile
  reads; days left without samples are found by that recompute and
  cleared in one statement instead of one query per day. Measured on 20
  such requests over an existing export: 43.0–45.1 → 24.4–27.2 s, the
  longest request 3.7–4.4 → 2.0–2.1 s, days recomputed 29 300 → 1 713;
  the same fingerprint of all days in each run (the old code varied on
  one day between runs, at the 17th digit).
- **A large metric is cut into periods computed at the same time**
  (for everyone; `RECONCILE_SPLIT_MIN_SAMPLES`, 100 000). A reconcile
  cannot be faster than its largest metric, which one process computed
  alone (5 s of ≈ 7 s at the user's). A metric with at least that many
  samples and more than one process's share of the account's is now cut
  at local midnights into periods of about a share each (log: «
  activity.active_energy 1/2 »). Each part reads a day more on each side
  and keeps only its own days, and the whole reconcile reads samples in
  the table's order (never the index's), so every day gets its samples
  in the same order: the same values to the last digit, split or not,
  1 or N processes (44 016 days, same md5; a test cuts across the change
  of time of 29 March). Test machine, 4 processes: 3.5 → 3.2 s; reading
  in table order costs nothing (1 process 7.8 → 7.8 s). At the user's
  (2 million samples, 16 threads): 1 process 17.7–18.7 → 14.0 s, 4
  processes 6.8–7.1 → 5.4 s, 8 processes 4.4 s, with the same md5 of
  all their days for 1, 4 and 8.
- **Every recompute of daily values reads the samples twice as fast**
  (for everyone: reconcile, iPhone sync, Health Auto Export, work
  entries). Reading a metric's samples cost more than computing its
  days, and half of the reading was SQLAlchemy's row objects: on
  PostgreSQL the samples are now read by asyncpg itself, with the very
  SQL SQLAlchemy compiles (same plan, same order of rows), in the same
  transaction. Reading only: 0.87–0.98 → 0.52–0.60 s for 372 316
  samples, 1.80–1.90 → 0.95–0.97 s for 930 782. Full reconcile on the
  test machine (medians, versions in turn): one process 10.4 → 7.6 s,
  two 5.4 → 3.9 s, four 3.9 → 3.0 s. (First published as « two 4.4 →
  4.0 s, four 3.5 → 3.5 s »: in that measurement the old version's
  processes, started with `python -m` from the new code's folder, ran
  the new code; each version now runs from its own folder.) The 44 016
  days written keep the same md5.
- **The reconcile no longer waits for its processes nor for its count
  check** (for everyone). Its `RECONCILE_PARALLEL` processes now start
  at the reconcile's beginning and load their code while the catalogue,
  the alias merge and the metric list run (1 to 2 s at the user's), and
  the raw samples' counts are rebuilt (a check) while the processes
  compute the days, instead of before (1.2 s at the user's); the counts'
  lock on the samples lasts as long as before. The days' computation is
  unchanged. Measured on the test machine (4 processes, both versions
  in turn, 5 times): 5.73 → 5.30 s median, faster each time; the 44 016
  days written keep the same md5 with 1, 4 and 8 processes and the
  counts are exact. On 4 cores the gain is small; at the user's (16
  threads, half free), measured after the update: 9.1–9.5 s → 6.8 and
  7.1 s (16.6 s before the reconcile used several cores).
- **PostgreSQL's memory is set in `.env`** (for the administrator):
  `DB_SHARED_BUFFERS`, `DB_EFFECTIVE_CACHE_SIZE`, `DB_WORK_MEM`,
  `DB_MAINTENANCE_WORK_MEM`, and `DB_SHM_SIZE` for parallel queries
  (Docker's 64 MB was too small once work_mem grows; now 256 MB, a
  ceiling). The defaults are PostgreSQL's own, so nothing changes until
  set. Measured on the test machine with 2 GB instead of 128 MB: no net
  gain there (reconcile 10.8 → 10.0 s, whole-table reads unchanged),
  since table scans bypass the buffers and the OS cache already holds
  everything. It may help a host short of cache (docs/performance.md).
- **Each account's history is reconciled once after an update of the
  hub** (for everyone, in the background). An update may change the
  catalogue or the day's rule, while the syncs only recompute the days
  they touch. The worker checks 2 min after it starts, then every hour,
  and reconciles the accounts not yet reconciled on this version
  (`users.reconciled_commit`, migration `0028`). A failure is tried
  again the next hour, and a reconcile done by hand counts. Settings:
  `RECONCILE_AFTER_UPDATE`, `RECONCILE_AFTER_UPDATE_DELAY_S`,
  `RECONCILE_CHECK_MINUTE`. The `reconciled` log line now gives the time
  taken (`seconds`) and the five slowest metrics (`slowest`).
- **Nothing that sizes, times or paces the hub is fixed in the code**
  (for the administrator): every value — database connections, worker
  jobs and time limits, gunicorn timeouts, nginx sizes, time limits,
  compression, buffers and cache, AI budgets and time limits, image
  sizes, upload limits, import and sync batches, Open Food Facts
  schedule, update detection, work and sleep rules (legal maxima, night
  hours, pairing windows), medication windows, photo quality and trend
  rules, late orders, and the web page's retries, polls, refreshes and
  « Par page » choices — is set in `.env`, with the old value as
  default (`backend/app/core/tuning.py`, `nginx/default.conf.template`,
  `docker-compose.yml`). All listed in `.env.example` and
  `docs/guides/configuration.md` (« Réglages de fonctionnement »); a
  test fails if one is added without its documentation. The page reads
  its own from `GET /system/settings` before it shows anything
  (fallback: the defaults). Kept in code on purpose: physical and
  format constants, reader internals, layout, and the official meal
  references.
- **A meal's AI reading can wait**: `POST /meals` takes
  `analysis_delay_min` (minutes; empty = at once, as before; at most
  `MEAL_ANALYSIS_MAX_DELAY_MIN`, 60 by default), and so does the MCP
  tool `log_meal`. Photos and changes sent meanwhile start nothing: the
  planned reading reads everything, once; the answer's `analysis_after`
  says when, the Journal shows « Analyse IA prévue à 20:32 » and
  « Réanalyser » reads it at once (migration `0026`).
- **A meal's nutrient table no longer widens the page on a phone**: with
  the references' columns it pushed the Journal 21 px sideways at
  390 px; it now scrolls inside its card.
- **`API_WORKERS`** (default 4, was a fixed 2): the API processes
  answering at the same time; each holds at most 10 database
  connections. Ten people opening Accueil then Santé together: a page in
  0.50 s with 4 processes instead of 0.74 s with 2.
- **API logs with the time and the duration**: each request has one
  line — UTC time (like nginx's), client, request, status, milliseconds;
  a request of a second or more ends with `slow`. nginx's lines end with
  `rt=` (total) and `api=` (the API's share). Every other API log line
  carries its UTC time too (first, or in a JSON line's `timestamp`).
  nginx keeps an API answer of up to 2 MB (a meal photo) in memory
  instead of a temporary file; a larger one still spills to a file, as
  before.
- **Sync from your own iPhone app: `POST /sync/healthkit`** — for an app
  reading HealthKit, incremental and without duplicates:
  - `samples` keyed by their HealthKit UUID (sent again = replaced),
    discrete quantities in HealthKit's own unit, categories by their
    `HKCategoryValue…` name, sleep by its stage number 0-5;
  - `statistics`: cumulative types (steps, distance, energy…) as
    HealthKit's hourly sums, so the iPhone and the watch never count
    twice; a batch replaces the sums it overlaps;
  - nights from the sleep stages — the Apple Watch's phases, the time
    in bed of every device (the iPhone's bedtime) with overlaps merged —
    into the daily `sleep.*` values and the Nuits view;
  - `workouts` by UUID, with the day's `workout.*` totals;
  - `deleted`: UUIDs removed in the Health app are removed here, and a
    day left empty loses its value;
  - refused lines are counted in `skipped` with their reason, never
    fatal; only the touched days are recomputed.
  The app's channel (`healthkit`) counts as one Apple channel a day with
  the native export and Health Auto Export. `GET /sync/healthkit` (and
  the MCP tool `iphone_app_sync`) says what the hub holds; Import › « App
  iPhone (HealthKit) » creates the app's token and shows the last sync.
  Migration `0024` adds `external_id` (unique per user) to raw samples
  and workouts. Full contract: ingestion guide.
- **Energy eaten on the home page**: a tile « Énergie apportée (repas) »
  (`nutrition.energy`: the day's kcal from analysed meals, plus any
  logged in Apple Health, with the last meal's time) sits next to
  « Énergie active » and « Énergie de repos » (`activity.basal_energy`,
  shown when the watch sends it) — what is spent is active + resting.
- **Each nutrient against official references**: a meal's table has a
  column « Repère dîner » (petit-déjeuner, déjeuner) with the part of an
  adult-type day that meal type carries — « 600–800 kcal », « 600–800 mg
  de sodium » — and a mark: ✓ within, ↓ below, ↑ above, ⚠ over a limit
  (sugars, saturates, sodium), ↓ in orange when fibre is short. Daily
  references: energy 2 000 kcal, protein 50 g, carbohydrate 260 g,
  sugars 90 g, fat 70 g, saturates 20 g (EU 1169/2011, annex XIII),
  fibre 30 g (ANSES 2016), sodium under 2 000 mg (WHO). The meal parts
  (breakfast 15–25 %, lunch and dinner 30–40 %) are the ANSES sheet
  « Veiller à son équilibre nutritionnel », shown as indicative: ANSES
  said in 2019 no split can be recommended, and none exists for a snack,
  which shows its share of the day (« 33 % »). The column follows the
  meal's type: a meal logged without one takes it from the hour (before
  10:30 breakfast…), so a dinner eaten at 5 am must be said « dîner »
  or corrected with « Modifier » — documented in the user, AI and MCP
  guides with the sources' links. Computed by the hub on
  each read (`reference` of `GET /meals/{id}`), never by the AI;
  `GET /nutrition/references` and the MCP tool `nutrition_references`
  give the table and its sources.
- **What a reference means, one tap away**: « Comprendre ces
  références » under each meal explains the reference column (values and
  links to the EU regulation, ANSES and WHO), Nutri-Score, NOVA 1–4,
  Ciqual, « étiquette », « estimé » and the quantity words. Each Ciqual
  line now names the table food used (« Ciqual « Tomate, crue » »), an
  « étiquette 🏷️ » line links to the product's Open Food Facts page,
  and a sheet's Open Food Facts details link to what Nutri-Score and
  NOVA mean.
- **Read Open Food Facts again without the pack**: « ↻ Open Food Facts »
  on each sheet that has a barcode re-reads its page and says what
  changed; « ↻ Tout relire sur Open Food Facts » does every sheet (a
  minute at most). Values the page gives, product details, the weight
  and brand when empty are replaced; name, units, usual portion, other
  names, note and photos stay. Each night the worker re-reads pages
  older than `FOOD_REFRESH_DAYS` (30 by default, 0: never; only with
  `FOOD_LOOKUP_ONLINE=true`). `POST /foods/{id}/refresh`, `POST
  /foods/refresh`, MCP `refresh_food`, `refresh_foods`.
- **Food stock**: « Stock » on a sheet of Mes aliments enters a
  purchase (« J'ai acheté »), a count (« Il m'en reste ») or a loss
  (« Jeté / donné »), in packs, units or grams, and shows what is left
  (« 370 g (2 × 185 g) ») with its history. Meals are never entered:
  what an analysed meal ate from a sheet is taken off by itself, so a
  meal changed, read again or deleted corrects the stock; a bought meal
  (with a price), a meal before the first purchase or before the last
  count does not count. New table `food_stock_moves` (migration
  `0022`); `GET/POST /stock` (`?token=` for the « Ranger les courses »
  iPhone Shortcut: scan each pack's barcode), `GET
  /stock/{food_id}/moves`, `DELETE /stock/moves/{id}`; MCP
  `food_stock`, `add_stock`, `stock_history`, `delete_stock_move`, and
  the assistant is told to suggest « what to cook tonight » from the
  stock only, within what is left.
- **One sheet per size, and my usual portion**: a food sheet has « Ma
  portion habituelle (g) », with « Toute la boîte », « ½ », « ¼ » to
  compute it from the package (migration `0021`, `portion_g`; MCP
  `save_food`). A meal naming a food without a quantity counts that
  portion (the whole small box, ¼ of the big one). Two sizes of one
  product are two sheets: everywhere a sheet shows « name · brand ·
  weight » (list, meal menu with its portion, analysis lines), and a
  description saying « petite boîte » takes the smaller package,
  « grosse / grande boîte » the larger, « boîte de 750 g » that one;
  « un quart de la grosse boîte » is ¼ of its weight. Sizes of one
  product are listed together, smaller first.
- **Barcode from a photo or the camera**: in Mes aliments › « ▥
  Code-barres (scan ou saisie) », « 📷 Scanner le code-barres » opens
  the camera and « 🖼️ Photo du code-barres » takes a photo from the
  gallery; the hub decodes it itself, offline (zxing-cpp, EAN-13,
  EAN-8, UPC), and the photo is not kept. A food of your list with that
  barcode is named, otherwise Open Food Facts proposes the product when
  `FOOD_LOOKUP_ONLINE=true` (the barcode only is sent), otherwise the
  code is put on the sheet. A « 📦 Photo de la boîte » showing the
  barcode fills the sheet's barcode too. In a meal (new or changed),
  « ▥ Scanner un code-barres » chooses your food with that barcode.
  `POST /foods/scan` (form `file`; `?token=` for an iPhone Shortcut),
  MCP `scan_barcode`.
- **The AI synthesis knows the adherence**: its facts now include, per
  treatment with doses recorded over the last 30 days, the doses taken
  out of planned, the rate, the days without any entry, the longest gap,
  the usual time and the late entries — it can state whether a treatment
  is followed from what was recorded.
- **Documentation with every change**: `CLAUDE.md` (rules for anyone
  changing the repository: privacy, isolation, and the documents every
  commit must update — changelog, user guide and iPhone Shortcut, API,
  MCP, security and configuration, data model, AI guide) and a
  pre-commit hook `docs-updated` (`tools/check_docs_updated.py`) that
  refuses code without CHANGELOG.md and a hand-written document.
- **Multi-user plan**: « Passer vos données de l'admin à votre compte —
  sans rien perdre » (preview table by table and files with SHA-256,
  automatic backup, one transaction, copy-verify-then-delete of files,
  counts and fingerprints checked, tokens and Shortcuts kept working).
- **Reports that prove the facts** (PDF clinique and synthèse):
  - header: report number, exact creation time and zone, version
    (`GIT_COMMIT`), how many values came from each source, SHA-256 of
    the data used; every page's footer repeats the report id and date;
  - « Habitudes enregistrées »: per counter, days recorded out of the
    period's days (a day without an entry is « sans donnée », never
    zero), total, mean per recorded day, median, lowest / highest day
    with their date; cigarettes day by day (gaps visible) and per week
    or month; « Comparer avant / après le » (new report option): means
    before and since, days on each side, change in %;
  - « Médicaments — observance » per treatment; « Alimentation » (meals,
    share read, daily means, AI scores, value origins, foods eaten most,
    per month, late entries); dated treatments, the period's
    appointments with the practitioner; yes / no answers counted;
  - « Traçabilité des saisies »: per counter, entries made the same day
    or afterwards and their channel; doses and meals entered within the
    hour (3 h), the same day, later.
- **Authentic copies**: each report's SHA-256 is stored and audited;
  « 🔏 Vérifier un fichier » / `POST /reports/verify` tells whether a
  copy is byte for byte one of your reports (migration `0020`).
- **« 0 » on a counter** (cigarettes, coffee, water): confirms a day at
  zero, so a report counts it instead of « sans donnée ».
- `GET /facts` (MCP `period_facts`): the same facts as JSON;
  « Heures de contrat par semaine » in the report form (work reports).
- **Medication doses and adherence**: each dose taken — or declared not
  taken — is recorded with the time it was taken, the time it was
  entered and the channel (web, iPhone Shortcut, MCP, token id): the
  proof a treatment is followed, and that it was noted at the time.
  Journal › Aujourd'hui › « 💊 Médicaments du jour » (✔ Pris, Pris à…,
  ✗ Non pris, ↶ Annuler); Suivi › Traitements gains « prises / jour »
  and a 30-day adherence line (rate, days without any record, usual
  time); the journal line counts the doses. `POST /medications/take`
  (by name, `?token=` for a Shortcut), `POST /treatments/{id}/intakes`,
  `GET /medications/intakes`, `/medications/today`,
  `/medications/adherence` (planned, taken, skipped, rate, days
  complete, days without record, longest gap, usual time, entered late,
  per week), `DELETE /medications/intakes/{id}` (audited). MCP
  `log_medication`, `medications_today`, `medication_intakes`,
  `medication_adherence`, `delete_medication_intake`. Migration `0019`
  (a deleted treatment keeps its doses, name and dose copied).
- **Edit a meal afterwards** (Journal › Repas › « Modifier »): type, date
  and time, description, foods of the list, and its photos — remove one
  (the plate's too) or add some later (a meal without a plate photo
  takes the first one added). « Enregistrer et réanalyser » applies all
  and reads the meal once. `POST /meals/{id}/photos` gives the plate's
  photo to a meal without one; `DELETE /meals/{id}/photo`; `?read=false`
  on photo changes; MCP `add_meal_photo`, `delete_meal_photo`
  (`update_meal` takes `foods`).
- **Same meal, same numbers — the Ciqual table**: the ANSES Ciqual 2025
  table (3,484 generic foods, Licence Ouverte, shipped with the hub,
  read offline; provenance in `backend/app/data/README.md`). The meal
  reading now works as « the AI recognises and weighs, the tables
  count »: the model picks each food's closest Ciqual reference from a
  short list built from the description's words (prepared as said —
  « cuit », « vapeur », « cru » — generic first), and code computes its
  values for the grams; a code outside the list, or anything the model
  writes as a source, is ignored. Values shown per food: « étiquette
  🏷️ », « Ciqual » or « estimé ». `GET /ciqual?q=` and `/ciqual/{code}`,
  MCP `search_ciqual`.
- **Quantities read by code**: for a food of « Mes aliments », the
  grams come from the description — « saumon 100g », « 150 g de riz »,
  « 2 tomates » (× the food's unit), « un demi concombre », « une
  tranche de comté », « ½ sachet de riz » (× the package) — never
  guessed twice differently. Food sheets gain a unit (« tomate » =
  120 g), a source and a barcode (migration `0018`).
- **Open Food Facts by barcode (opt-in)**: « Code-barres » in Mes
  aliments fills a sheet from a product's barcode when
  `FOOD_LOOKUP_ONLINE=true` (off by default; only the barcode is sent).
  `GET /openfoodfacts/{barcode}`, MCP `lookup_barcode`.
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
