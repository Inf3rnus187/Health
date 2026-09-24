# Phoenix Health Hub

> Self-hosted, extensible personal **health & training** hub — powered by an
> API, scripts and the Apple Watch, with dynamic metrics, dashboards and
> AI photo analysis. *Phoenix Health Hub* is a working name.

Centralise **all** your health and training data (weight, sleep + CPAP,
Apple Watch vitals, workouts, walks, treatments, symptoms, progress photos)
in one hub you host yourself with Docker.

Guiding constraints (non‑negotiable):

- **Hot extensibility** — add a new metric with **no schema migration and no
  redeploy** (it is a row in `metric_definitions`).
- **Zero redundancy** — each value is stored once; rolling averages and
  derived values (e.g. `litres = bottles × 1.5`) are **computed, never
  re‑entered**.
- **Multi‑source ingestion** — UI, REST API, scripts, scoped tokens, Apple
  Watch webhooks.
- **Multi‑user by design**, with strict per‑user isolation (every row has
  an owner, every query filters on it). There is **no way yet to create a
  second account**: the hub runs with the single admin account created at
  install — see the [multi-user plan](docs/multi-utilisateur.md).

---

## Status — what this milestone delivers

All phases of the [roadmap](docs/architecture.md#roadmap) are implemented
and tested:

| Area | Status |
|------|--------|
| Docker Compose stack (db, redis, api, worker, web, mcp) | ✅ |
| Auth: JWT access + **rotating refresh** + revocation; roles `admin` / `user` (one seeded admin account today) | ✅ |
| Scoped, hashed **API tokens** (machine access); a token sent in the URL (`?token=`, iPhone Shortcuts) is written `token=***` in the API and nginx logs | ✅ |
| **Admin role**: host updates (`/system/update`, admin web session only) and the shared metric catalogue (`POST`/`PATCH /metrics`) | ✅ |
| **Audit log** of every write | ✅ |
| **Dynamic metric registry** (add a field at runtime) | ✅ |
| Idempotent **batch measurements** + events (zero redundancy) | ✅ |
| Rolling aggregates (7/30 j) computed on read | ✅ |
| **Seed catalogue** — the full Annexe A dictionary (77 metrics) | ✅ |
| React front: login, catalogue, governed chart, quick entry | ✅ |
| Quality gates: ruff, mypy strict, ESLint, custom limits, CI, coverage ≥80% | ✅ |
| **Ingestion** `/ingest/watch` + `/ingest/ppc` + configurable HealthKit mapping | ✅ |
| **Mode B** `/capture` (opens session, pre‑fills night data, returns form) | ✅ |
| **Photo pipeline** (upload → EXIF‑strip/normalize → Ollama vision → compare) | ✅ |
| **Dashboards** per domain (`/dashboard/{domain}` + React domain tabs) | ✅ |
| **Exports** of daily values CSV/JSON/XLSX/FHIR + async **clinical PDF** reports | ✅ |
| **MCP server** — 105 tools covering the whole hub, as a REST‑API client (each client uses its own `hub:full` token) | ✅ |
| **Automations** (trigger→action: reminder/capture) + run endpoint | ✅ |
| **Hardening**: optional TOTP MFA (API only, no web screen yet), at‑rest file encryption, RGPD erasure | ✅ |
| **Supply chain**: gitleaks, pip‑audit, pnpm audit, Trivy, syft SBOM (CI) | ✅ |
| **Apple Health import** (web + API): all raw samples, workouts, ECG, GPS, CDA | ✅ |
| ECG waveform & GPS route **viewers**; day/week/month/year charts + wheel zoom | ✅ |
| **iPhone sync** — SimpleHealthExportCSV zip upload (auto‑detected import) | ✅ |
| **Dark theme** + mobile‑responsive layout | ✅ |
| **Multi‑page UI** (Accueil/récap · Tableaux de bord · Santé · Données · Rapports · Import) | ✅ |
| **Rapports** (générer PDF clinique/CSV/JSON/XLSX/FHIR + télécharger) & **exports** dans l'UI | ✅ |
| **Complete Apple Health catalog** (iOS 26 SDK: 121 quantity + 72 category types, French labels) + **Health Auto Export** | ✅ |
| **One truth**: canonical keys, daily values rebuilt from raw samples, *Réconcilier*, same numbers on every page | ✅ |
| **Medical record** (Dossier): documents read by **MedGemma** with values checked against the text, results + source, chronology, suggestions | ✅ |
| **Suivi**: each condition with its indicators and documents; treatments with their doses per day and a 30-day adherence line (rate, days without any record, usual time) | ✅ |
| **Évolution**: validated markers (FibroScan, FLI, FIB-4, HbA1c…), weight milestones, longitudinal photo method | ✅ |
| **AI clinical synthesis** report: every sentence cites the record's facts, unproven ones removed | ✅ |
| **Rapports that prove the facts**: habits (days recorded, « sans donnée » never counted as zero), medication adherence, meals, traceability of entries (same day or later, channel), before / after comparison; each page stamped (report id, time, version); SHA-256 stored, « Vérifier un fichier » (`POST /reports/verify`) checks a copy | ✅ |
| **Journal** — Aujourd'hui: last night, counters (water, coffee, cigarettes, pee) with « +1 » / « − » and « 0 » to confirm a day at zero, today's medications (taken / not taken); Mon journal: one line per day | ✅ |
| **Meals**: up to 7 photos (plate, box, label), description, edit afterwards, « Refaire ce repas »; the AI recognises and weighs, values computed by code from the ANSES **Ciqual** table (shipped, offline) or the food's label — same meal, same numbers | ✅ |
| **Mes aliments**: foods eaten often with their values per 100 g, label read from a photo (vision model), barcode lookup on Open Food Facts (opt-in, `FOOD_LOOKUP_ONLINE`, barcode only) | ✅ |
| **Travail**: clock in / out (GPS Shortcut, web, assistant), on site or remote, hours worked per day, overtime, 10 h / 48 h flags, 7 d → 1 y stats, CSV / Excel / PDF, import of past txt / csv / json logs; absences with half days, imported from HR exports (Lucca…); Uber Eats / meals spending; bulk delete of sessions, absences, proofs and meals | ✅ |
| **Work ↔ health file**: incomplete and 72 h sessions, sick-leave periods with causes, evidence (calls, mails, screenshots) with SHA-256, nights (awakenings, fragmented sleep, typed nights), legal landmarks, sleep correlations, full PDF report with evidence annex; import of iPhone Shortcut histories; **traces** (transport, taxi, parking, deliveries, hotels, expense reports) imported from Uber / Uber Eats / Navigo / parking / bank exports, deliveries logged as priced meals read by the AI; WhatsApp chat exports, ticket exports (NinjaOne…) and Lucca expense-report PDFs read as proofs and traces | ✅ |
| **Update notice**: the page offers « Recharger » after a new build (`/version.json`); `./update.sh` pulls and rebuilds only what changed; with its cron, the admin sees « Mise à jour disponible » and « Installer » (no Docker socket in any container) | ✅ |

**All 9 specification phases are implemented.** Remaining follow‑ups
(signed container images, encrypted off‑site backups, an automated retention
purge job) and known limitations (single account, MFA without a web
screen, no login rate limit…) are noted in [`SECURITY.md`](SECURITY.md).

See [`docs/`](docs) for architecture, the data model, and how‑to guides.

---

## Quick start (Docker)

Requirements: Docker + Docker Compose.

```bash
git clone <this-repo> phoenix-health-hub
cd phoenix-health-hub
cp .env.example .env      # then edit it BEFORE the first ./install.sh
./install.sh              # build + migrate + seed + create admin + start
```

Then open **http://localhost:8082** and log in with the `ADMIN_EMAIL` /
`ADMIN_PASSWORD` from your `.env`. Interactive API docs live at
**http://localhost:8082/api/v1/docs** (Swagger) and `/api/v1/redoc`.

`install.sh` is the single bootstrap: it creates `.env` with a strong random
`SECRET_KEY` on first run, builds the images, applies migrations, seeds the
metric catalogue and admin user (idempotently), then starts the stack. It
does not stop to let you edit a `.env` it has just created, so set
`ADMIN_EMAIL`, `ADMIN_PASSWORD` and `POSTGRES_PASSWORD` first: the admin
account is created once, and no route changes its password afterwards.

> TLS is intentionally **not** provided: the app only speaks HTTP internally.
> Terminate HTTPS with your own reverse proxy in front of the `web` service.

---

## Configuration

Everything is configured through environment variables — see the fully
commented [`.env.example`](.env.example). Key settings:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing key (≥32 chars; auto‑generated by `install.sh`). |
| `POSTGRES_USER/PASSWORD/DB` | Database credentials. |
| `ADMIN_EMAIL/PASSWORD` | Initial admin created by the seed step (read only when that account does not exist yet). |
| `ACCESS_TOKEN_TTL_MIN` / `REFRESH_TOKEN_TTL_DAYS` | Token lifetimes. |
| `OLLAMA_URL` / `OLLAMA_*_MODEL` | AI endpoint + one model per task (photos, documents, synthesis — MedGemma recommended). |
| `WEB_PORT` | Host port for the web tier (default 8082). |
| `MCP_BIND` / `MCP_PORT` / `MCP_TRANSPORT` | MCP server (optional; clients use their own `hub:full` token). |

Every variable is explained in the
[configuration guide](docs/guides/configuration.md).

---

## Documentation

| Guide | Contenu |
|-------|---------|
| [Configuration](docs/guides/configuration.md) | Installer, mettre à jour, toutes les variables, jetons et scopes, services, journaux. |
| [Utilisation](docs/guides/utilisation.md) | Chaque page (Accueil, Données, Dossier, Photos, Suivi, Rapports, Import…) et les parcours types. |
| [IA médicale](docs/guides/ia-medicale.md) | MedGemma par tâche, lecture des documents et valeurs rejetées, synthèse clinique, méthode photo, dépannage. |
| [Ingestion](docs/guides/ingestion.md) | Apple Santé, Health Auto Export, Raccourcis, montre, PPC, photos. |
| [MCP](docs/guides/mcp.md) | Brancher un assistant (Claude Desktop / Code, stdio) de façon sûre. |
| [Référence API](docs/api.md) | Toutes les routes, leurs paramètres et le droit exigé (générée depuis le code). |
| [Outils MCP](docs/mcp-tools.md) | Les 105 outils et leurs paramètres (générée depuis le serveur). |
| [Multi-utilisateur](docs/multi-utilisateur.md) | Ce qui manque pour plusieurs comptes (on ne peut pas encore en créer un second) : analyse et plan. |
| [Sécurité](SECURITY.md) | Niveaux d'accès, chiffrement, limites connues. |
| [Architecture](docs/architecture.md), [modèle de données](docs/data-model.md), [ADR](docs/adr/) | Conception. |

---

## Using the API

```bash
BASE=http://localhost:8082/api/v1

# 1. Log in
ACCESS=$(curl -s $BASE/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<your password>"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 2. Add a brand-new metric at runtime (no migration!) — admin role only:
#    the catalogue is shared by every account
curl -s $BASE/metrics -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"key":"mind.meditation_min","label":"Méditation","domain":"mind",
       "data_type":"duration","unit":"min"}'

# 3. Record measurements (idempotent by date+metric)
curl -s $BASE/measurements -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"metric_key":"body.weight","date_key":"2026-01-15",
       "value":86.4}]}'

# 4. Read a rolling 7-day trend
curl -s "$BASE/measurements/series?metric_key=body.weight&agg=avg&window=7" \
  -H "Authorization: Bearer $ACCESS"

# 5. List raw measurements (optionally filtered) to grab their ids
curl -s "$BASE/measurements?metric_key=body.weight" \
  -H "Authorization: Bearer $ACCESS"

# 6a. Delete a single measurement by id
curl -s -X DELETE $BASE/measurements/<id> \
  -H "Authorization: Bearer $ACCESS"

# 6b. Delete several at once (returns {"deleted": N})
curl -s $BASE/measurements/delete -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"ids":["<id1>","<id2>"]}'
```

Seed a few fake rows, check the dashboard, then remove them — the same
delete actions are available in the web UI under the **Données** card
(tick one or more rows and press *Supprimer*).

Machine access uses **scoped tokens** instead of a login:

```bash
curl -s $BASE/tokens -H "Authorization: Bearer $ACCESS" \
  -H 'Content-Type: application/json' \
  -d '{"name":"apple-watch","scopes":["ingest:watch","write:measurements"]}'
# → returns the plaintext token ONCE; store it in your Shortcut.
```

Scopes are least-privilege: no write scope opens the **read** routes.
`ingest:*` tokens only send data. `write:measurements` sends,
but also **edits** (meals, foods, work sessions) and **deletes by id**
(measurements, meals and their photos, foods and their photos, pee
entries, work sessions, medication doses — including the batch
`/measurements/delete`, `/meals/delete`, `/work/sessions/delete`).
`write:metrics` works for the admin only (shared catalogue). Reading
health data (values, export, reports, photos, record) needs `read:all`;
`hub:full` (MCP / assistant) can do everything the web app does except
managing tokens, 2FA, deleting the account, downloading the Shortcut and
`/system/update`. Wiping everything (all photos, Apple import reset)
needs a login or `hub:full`. Access levels in detail:
[SECURITY.md](SECURITY.md#access-levels).

Adding a metric is also documented step‑by‑step in
[docs/guides/add-a-metric.md](docs/guides/add-a-metric.md).

---

## Importer vos données Apple Santé

Depuis l'app **Santé** sur iPhone : votre photo de profil → **Exporter
toutes les données de santé**. Vous obtenez un `export.zip` contenant un
gros `export.xml` (souvent plusieurs centaines de Mo), `export_cda.xml`,
et les dossiers `electrocardiograms/` et `workout-routes/`.

**Tout est importé, sans rien jeter** : chaque échantillon brut (des
millions de lignes), chaque séance, chaque ECG et chaque tracé GPS.

### Depuis le site (recommandé)

Connectez-vous, ouvrez la carte **Importer mes données Apple Santé**,
choisissez votre `export.zip` (ECG et tracés inclus) et cliquez
**Importer**. Le fichier est envoyé en flux (aucune limite de taille sur
cette route), traité en tâche de fond par le worker, et la carte affiche
la progression puis le décompte final (échantillons / séances / ECG /
tracés). Le bouton **Supprimer les données importées** efface tout.

### Depuis l'API

```bash
BASE=http://localhost:8082/api/v1
# ACCESS = jeton obtenu via /auth/login (voir plus haut)
curl -s "$BASE/imports/apple-health" -H "Authorization: Bearer $ACCESS" \
  -F "file=@export.zip"                 # → renvoie un job {id,status}
curl -s "$BASE/imports/<id>" -H "Authorization: Bearer $ACCESS"  # statut
```

### En ligne de commande (très gros fichiers)

```bash
docker compose exec api \
  python -m app.cli.import_apple_health /import/export.zip
```

### Ce que l'import stocke

- **Tous les échantillons bruts** dans `health_samples` (valeur, horodatage
  exact, unité, appareil) — parcourables page par page dans la carte
  **Données brutes** (filtre par métrique et par dates ; jamais de scroll
  infini, même avec des millions de lignes).
- **Séances** (`workouts`), **ECG** (`ecg_records`, tracé complet chiffré
  sur disque) et **tracés GPS** (`route_files`, GPX conservé), listés dans
  leurs cartes dédiées et **visualisables** dans le site :
  - l'ECG s'affiche en **courbe de tension** (bouton *Voir*), téléchargeable
    en CSV ;
    - le tracé GPS s'affiche sur une **vraie carte** (Leaflet), GPX
      téléchargeable. Fond de carte configurable dans `.env` (rebuild
      `web` ensuite) :
      - **clé API** (recommandé) : créez-en une gratuite sur
        [MapTiler](https://cloud.maptiler.com) et mettez `VITE_MAP_KEY=…` ;
      - sinon, fond **Carto** par défaut, sans clé (les serveurs publics
        d'OpenStreetMap **bloquent** les apps tierces, d'où ce choix) ;
      - `VITE_TILE_URL` / `VITE_TILE_ATTRIB` pour tout autre fournisseur
        (ajoutez son domaine à `img-src` dans `nginx/default.conf`) ;
        `VITE_TILE_URL=none` = trace seule, sans fond ni appel externe.
      La carte est la seule exception à la CSP « self ».
  - Les ECG marqués **« mauvais enregistrement »** (Poor Recording) sont
    **ignorés** à l'import.
- Le **document clinique CDA** (`export_cda.xml`) est analysé : chaque
  observation (analyses, constantes…) est extraite dans
  `clinical_observations` et consultable dans la carte **Documents
  cliniques** (recherche + pagination) ; le XML brut reste téléchargeable.
- En plus du brut, un **résumé quotidien** par métrique est mis en cache
  dans `measurements` pour que les tableaux de bord restent traçables
  (les points, l'énergie et les minutes sont sommés ; la FC, la SpO2 et la
  respiration moyennées ; poids/IMC/taille = dernière valeur du jour). Les
  tableaux de bord se règlent par **jour / semaine / mois / année** et la
  **molette zoome** l'axe du temps.
- Les unités Apple (`mi`, `lb`, `mL`, `degF`, `%` fractionnel…) sont
  converties. Chaque type Apple a son libellé français et son domaine
  (catalogue complet du SDK iOS 26) ; un type hors catalogue est créé
  automatiquement (sans migration) sous le domaine `apple`.
- **Rejouable** : réimporter remplace proprement les données Apple
  précédentes (aucun doublon).

Détails d'architecture dans
[docs/adr/0006-apple-health-import.md](docs/adr/0006-apple-health-import.md).

### Synchro iPhone (raccourci d'export CSV)

Le web **ne peut pas** lire HealthKit, et iOS **refuse d'importer un
raccourci non signé** (la signature Apple exige un appareil Apple — donc
impossible à fabriquer côté serveur). La voie fiable utilise un raccourci
**déjà signé et distribué** : **SimpleHealthExportCSV** (RoutineHub,
gratuit). Il exporte tes données Santé en CSV (un fichier par type),
zippés, et sait les **uploader** vers une URL.

La page **Import → « Synchro iPhone »** génère une **URL d'upload avec le
jeton déjà inclus** (`write:measurements`) — aucun en-tête à saisir. Dans
l'action d'envoi du raccourci (« Obtenir le contenu de l'URL ») :

- **URL** : `https://TON-SERVEUR/api/v1/imports/apple-health?token=<jeton>`
- **Méthode** : `POST`
- **Corps** : `Formulaire` → un champ **Fichier** nommé **`file`** = le
  `.zip`

Le jeton s'accepte aussi via l'en-tête `Authorization: Bearer <jeton>` si
tu préfères ; le paramètre `?token=` évite juste la saisie fragile de
l'en-tête sur mobile (jeton scoped et révocable, réseau local).

Le serveur avale ce zip de CSV **exactement** comme l'`export.xml`
d'Apple : stockage full-fidélité (`health_samples`), roll-ups quotidiens,
et création à la volée des métriques `apple.*` pour les types inconnus.
L'upload web du `zip` (export Santé natif, avec ECG et CDA) reste la voie
de référence — un seul fichier, sans rien sélectionner.

---

## Development

Backend (Python 3.11+, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check app tests && ruff format --check app tests
mypy app
python ../tools/check_code_limits.py app     # §14.1 structural limits
pytest                                        # ≥80% coverage
python -m app.cli.api_doc > ../docs/api.md    # after changing a route
```

Frontend (Node 22, pnpm):

```bash
cd frontend
pnpm install
pnpm typecheck && pnpm lint && pnpm build
pnpm dev            # Vite dev server, proxies /api to localhost:8000
```

Install the git hooks once with `pre-commit install` (see
[`.pre-commit-config.yaml`](.pre-commit-config.yaml)). CI
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the same gates
and fails the build on any violation or coverage under 80%.

---

## Data, backup & restore

Docker named volumes hold all state: `pgdata` (database), `media` (photos,
documents, proofs, ECG and GPS files), `exports` (generated reports,
uploaded Apple exports). Back up **`.env`** too, and keep it safe: it
holds the passwords, `SECRET_KEY` and `MEDIA_ENCRYPTION_KEY` — without
that key, the encrypted files of `media` are lost for good. The `run/`
folder (update status) and `import/` need no backup.

```bash
# Backup the database
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > backup_$(date +%F).sql

# Restore
cat backup_YYYY-MM-DD.sql | docker compose exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Backup media/exports volumes
docker run --rm -v phoenix-health-hub_media:/data -v "$PWD":/out alpine \
  tar czf /out/media_$(date +%F).tgz -C /data .
```

---

## Project structure

```
phoenix-health-hub/
├── docker-compose.yml      # db, redis, api, worker, web, mcp
├── install.sh              # one-shot bootstrap
├── backend/                # FastAPI, SQLAlchemy, Alembic, tests
│   └── app/{core,models,schemas,services,api,workers,seed}
├── frontend/               # React + Vite + TS (theme, api, components)
├── nginx/                  # reverse proxy + React build image
├── mcp/                    # MCP server (105 tools, API client)
├── tools/                  # custom code-limit checker
└── docs/                   # architecture, data model, guides, ADRs
```

## Troubleshooting

- **Catalogue shows "NetworkError" / stays empty in the browser.** A
  tracking/ad blocker (or Firefox Enhanced Tracking Protection) is dropping
  requests whose path contains `metrics`. The web app fetches the catalogue
  from the `/api/v1/catalog` alias to avoid this; the canonical
  `/api/v1/metrics` endpoints remain for API clients, scripts and the MCP
  server. If you block `/catalog` too, allow this site in your blocker.

## Security

Argon2id passwords, short JWTs with rotating/revocable refresh sessions,
hashed scoped tokens, strict input validation, security headers + CSP,
an append‑only audit log, optional TOTP MFA (API only: no code field in
the web login yet) and at-rest file encryption, SBOM and dependency /
filesystem scans in CI. Tokens that only send data cannot read it
(`read:all`); tokens sent in the URL never reach the logs; the MCP server
only accepts `hub:full` tokens and relative API paths. Access levels,
what is and is not encrypted, and known limitations: see
[SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). Chosen as a permissive default; switch to AGPL‑3.0 if you
prefer network‑copyleft for a hosted service.
