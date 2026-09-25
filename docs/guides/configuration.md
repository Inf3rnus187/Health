# Guide — installation, configuration, mise à jour

Tout se règle dans le fichier `.env` à la racine (modèle commenté :
[`.env.example`](../../.env.example)). Après une modification :
`docker compose up -d` (et `--build` si le code a changé).

## Installer

```bash
git clone <ce-dépôt> phoenix-health-hub && cd phoenix-health-hub
cp .env.example .env   # puis éditer .env AVANT le premier ./install.sh
./install.sh           # build, migre, seed (compte admin), démarre
```

**Éditer `.env` avant le premier `./install.sh`.** Sans `.env`, le script
le crée depuis `.env.example` (seul `SECRET_KEY` est tiré au hasard) et
enchaîne aussitôt build, migrations et création du compte : les valeurs
d'exemple (`ADMIN_PASSWORD`, `POSTGRES_PASSWORD`) seraient alors en
service. À régler d'abord : `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
`POSTGRES_PASSWORD`, `DEFAULT_TIMEZONE`, et `MEDIA_ENCRYPTION_KEY` si
les fichiers doivent être chiffrés dès le départ.

`ADMIN_EMAIL` / `ADMIN_PASSWORD` ne servent qu'à **créer** le compte,
lors du seed de `install.sh`, et seulement si aucun compte n'a cet
e-mail (`backend/app/seed/seed.py`). Les changer ensuite ne change pas
le mot de passe (aucune route ne le permet aujourd'hui) ; changer
`ADMIN_EMAIL` puis relancer `./install.sh` crée un **second** compte
admin, vide. De même, l'image PostgreSQL n'applique `POSTGRES_USER` /
`POSTGRES_PASSWORD` / `POSTGRES_DB` qu'à la création du volume
`pgdata`.

Ouvrir `http://<machine>:8082` (port `WEB_PORT`) et se connecter avec
`ADMIN_EMAIL` / `ADMIN_PASSWORD`.

## Comptes et rôles

Seul le compte créé par le seed existe, avec le rôle `admin`. Aucune
route ni page ne crée d'autre compte ni ne change un rôle pour l'instant
(plan : [multi-utilisateur](../multi-utilisateur.md)). Réservé à
l'administrateur : la mise à jour depuis la page (`/system/update`,
session web uniquement) et le catalogue de métriques partagé
(`POST /metrics`, `PATCH /metrics/{key}`).

**2FA (TOTP)** : elle ne s'active que par l'API
(`POST /auth/mfa/setup` puis `/auth/mfa/enable`, avec une session web).
La page n'a ni écran de configuration ni champ de code à la connexion :
une fois la 2FA activée, **la connexion web est impossible**. Ne pas
l'activer sur le compte utilisé dans le navigateur.

## Mettre à jour

```bash
./update.sh      # git pull, puis ne reconstruit que ce qui a changé
```

`update.sh` remplace `git pull && docker compose up -d --build && docker
compose --profile mcp up -d --build mcp` :

- `git pull --ff-only` : une modification locale ou un historique divergent
  **arrête** la mise à jour, rien n'est écrasé (le message dit de regarder
  `git status`) ; `.env` et les volumes de données ne sont jamais touchés ;
- ne reconstruit que les parties changées : `backend/` → `api` et `worker`
  (les migrations s'appliquent au démarrage de l'API), `frontend/` ou
  `nginx/` → `web`, `mcp/` → `mcp` (s'il tourne), `docker-compose.yml` →
  tout ; documentation seule → rien ;
- `./update.sh --check` dit seulement ce qu'une mise à jour apporterait.

**Notification dans la page.** Toutes les 5 minutes, la page compare sa
version à celle installée (`/version.json`, une par construction de
l'interface) : après une mise à jour, « **Nouvelle version installée —
Recharger** ». Pour être prévenu **avant**, et installer d'un clic :

```bash
./update.sh --install-cron     # une fois ; ajoute à la crontab de l'utilisateur :
# * * * * * cd <dossier> && ./update.sh --cron >> run/update.log 2>&1
```

Chaque minute, le cron exécute une mise à jour demandée depuis la page ;
toutes les 5 minutes, il regarde GitHub (`git fetch`) — `./update.sh --check`
le fait tout de suite. Rien ne s'installe sans votre clic, sauf en mode
automatique : `./update.sh --install-cron --auto` (remplace la ligne cron)
installe seul chaque mise à jour trouvée ; `./update.sh --install-cron` revient
au clic. Le bandeau n'apparaît que s'il y a des changements à installer sur
la branche suivie par l'hôte (`git status` la nomme). La page affiche alors
« **Mise à jour disponible** : 3 changements — à reconstruire sur l'hôte :
interface web, API et worker » (ou « rien à reconstruire, documentation
seulement »), la liste des changements, « **Installer** » et « Plus tard ».
Sans le cron, la page donne la commande à lancer sur l'hôte.

**Réservé à l'administrateur** (compte au rôle `admin`) : l'état de
l'hôte, « Mise à jour disponible », « Installer », « Relancer ». Les
autres comptes voient seulement « Nouvelle version installée sur le
serveur : recharge la page » quand l'interface a changé.

Sécurité : la page ne pilote jamais Docker (pas de `docker.sock` dans un
conteneur, qui donnerait la main sur l'hôte). « Installer » dépose seulement
un fichier de demande dans `run/` (monté dans l'API en `/data/update`, créé
par `install.sh` et `update.sh`, droits `1777`) ; c'est le cron de l'hôte,
avec vos droits, qui fait `git pull` et reconstruit. Pendant la
reconstruction, l'API redémarre : la page est indisponible une à deux
minutes, puis propose de recharger. Suivi : `run/update.log`,
`run/status.json`.

**La version chargée** s'affiche à droite du nom, en haut de chaque page :
« v20c48fe · 24/09 20:52 » — le commit construit et l'heure de la
construction (sur téléphone, le commit seul). Après une mise à jour et
« Recharger », c'est là qu'on voit que la nouvelle version tourne.
`update.sh` et `install.sh` donnent le commit à l'image ; construite à la
main (`docker compose up -d --build`), la page affiche « version du … »
(ou passer `GIT_COMMIT=$(git rev-parse --short HEAD)` devant la commande).

Le bandeau dit toujours où en est l'hôte, avec l'heure :
« Mise à jour demandée à 20:41 : l'hôte la lance dans la minute », « en
cours depuis 20:42 », puis « ✓ À jour (20c48fe) ; reconstruit : web —
installée à 20:46 » (bouton « Masquer »). Une demande que l'hôte ne prend
pas en 3 minutes, ou une mise à jour sans nouvelles depuis 20 minutes,
s'affiche en rouge avec la commande à regarder (`tail -50
run/update.log`), « **Relancer la mise à jour** » et « Masquer » — plus
jamais « en cours » sans fin. Une mise à jour interrompue (erreur,
arrêt, redémarrage de l'hôte) est notée « échouée », jamais laissée « en
cours ».

`run/` est souvent créé par root ou par Docker (droits `1777`, « sticky ») :
l'utilisateur du cron ne peut alors pas supprimer la demande déposée par
l'API. `update.sh` ne la supprime plus : il en garde une copie
(`run/update-taken`) qui la marque prise en charge. Un hub resté bloqué
sur « Mise à jour en cours » avant cette correction : lancer une fois
`./update.sh` à la main sur l'hôte (le log montrait « rm: cannot remove
'run/update-request': Operation not permitted »).

**Options de `update.sh`** (en-tête du script) :

| Commande | Effet |
|----------|-------|
| `./update.sh` | Met à jour maintenant. |
| `./update.sh --check` | `git fetch`, écrit `run/update.json` (ce qu'une mise à jour apporterait). |
| `./update.sh --cron` | Pour le cron, chaque minute : écrit `run/heartbeat`, exécute une demande de la page, regarde GitHub toutes les 5 min. |
| `./update.sh --cron --auto` | Pareil, et installe seul une mise à jour trouvée. |
| `./update.sh --install-cron [--auto]` | Ajoute la ligne cron de l'utilisateur (remplace une ligne `--cron` existante). |

`COMPOSE` choisit la commande compose (défaut `docker compose`, ex.
`COMPOSE=docker-compose ./update.sh`).

**Prérequis du cron.** Le cron n'a pas de terminal : `git fetch` et
`git pull` doivent passer **sans mot de passe** (clé SSH sans phrase de
passe, gestionnaire d'identifiants, ou dépôt public). Le script pose
`GIT_TERMINAL_PROMPT=0` : un dépôt qui demande un mot de passe échoue
au lieu de bloquer. Le `PATH` du cron étant minimal, le script ajoute
`/usr/local/bin:/usr/bin:/bin:/snap/bin` pour trouver `docker`.

**« Installer »** n'est proposé que si le cron a battu il y a moins de
3 minutes (`run/heartbeat`, `backend/app/services/updates.py`) ; sinon
la page affiche la commande à lancer, et `POST /system/update` répond
`409`.

Fichiers de `run/` :

| Fichier | Contenu |
|---------|---------|
| `update.json` | Changements en attente, parties à reconstruire, commit actuel et dernier. |
| `status.json` | Dernière mise à jour : état (`running`, `done`, `failed`), message, heure, commit. |
| `heartbeat` | Heure du dernier passage du cron. |
| `update-request` | Demande déposée par l'API (« Installer »). |
| `update-taken` | Copie de la demande prise en charge par l'hôte. |
| `update.lock` | Verrou : une seule mise à jour à la fois. |
| `update.log` | Sortie du cron (redirection de la ligne cron). |

Puis, si la mise à jour touche les données (voir le CHANGELOG) :

1. **Données › Réconcilier** — recalcule les valeurs journalières depuis les
   relevés bruts, fusionne les clés en double, aligne le catalogue Apple.
   Aucune IA, tourne dans le worker (quelques minutes pour des années de
   données).
2. **Dossier › Analyser tous les documents (IA)** — relit chaque document
   avec les modèles actuels.
3. **Photos › Évolution › Réanalyser tout l'historique** — seulement si le
   modèle de vision a changé.

## Services (docker compose)

| Service | Rôle |
|---------|------|
| `db` | PostgreSQL (volume `pgdata`). |
| `redis` | File des tâches de fond. |
| `api` | FastAPI (`/api/v1`), applique les migrations au démarrage ; lit `run/` (état des mises à jour). Appelle aussi Ollama : lecture d'une étiquette nutritionnelle (Mes aliments) et, quand la file (Redis) est indisponible, rapport construit sur place, synthèse clinique comprise. |
| `worker` | Tâches longues : imports Apple, lecture IA des documents, des photos et des repas, rapports, réconciliation. |
| `web` | Nginx + interface React, port `WEB_PORT`. |
| `mcp` | Serveur MCP (optionnel, profil `mcp`), publié sur `MCP_BIND:MCP_PORT` (pas derrière nginx) — voir le [guide MCP](mcp.md). |

Volumes et dossiers montés :

| Volume / dossier | Monté dans | Contenu |
|------------------|-----------|---------|
| `pgdata` | `db` | La base PostgreSQL. |
| `media` | `api`, `worker` (`/data/media`) | Photos, documents, preuves, ECG, tracés (chiffrés si `MEDIA_ENCRYPTION_KEY`). |
| `exports` | `api`, `worker` (`/data/exports`) | Rapports, exports Apple envoyés (`imports/`), tampon d'envoi (`tmp/`). |
| `./run` | `api` (`/data/update`) | Échange avec `update.sh` (voir plus haut). |
| `./import` | `api` (`/import`, lecture seule) | Export Apple à importer en ligne de commande : `docker compose exec api python -m app.cli.import_apple_health /import/export.zip`. |

Journaux utiles :

```bash
docker compose logs worker --since 30m     # lecture IA, imports, rapports
docker compose logs api --since 30m
docker compose ps
```

## Variables d'environnement

### Cœur et sécurité

| Variable | Défaut | Rôle |
|----------|--------|------|
| `SECRET_KEY` | — (obligatoire, ≥ 32 car.) | Signe les sessions (JWT). Générée par `install.sh`. |
| `ACCESS_TOKEN_TTL_MIN` | `15` | Durée du jeton d'accès. La page web le renouvelle seule (toutes les 12 min, et à la première réponse 401) avec le jeton de rafraîchissement : une page restée ouverte ne se déconnecte pas. |
| `REFRESH_TOKEN_TTL_DAYS` | `14` | Durée maximale d'une connexion. |
| `JWT_ALGORITHM` | `HS256` | Algorithme de signature. |
| `CORS_ORIGINS` | vide | Origines navigateur autorisées (vide = même origine). |
| `ENV`, `DEBUG`, `APP_NAME`, `API_V1_PREFIX` | | Réglages généraux (laisser tels quels). |
| `MFA_ISSUER` | `Phoenix Health Hub` | Nom affiché dans l'application 2FA (TOTP). La 2FA n'a pas d'écran dans la page (voir « Comptes et rôles »). |

### Base, compte initial, région

| Variable | Rôle |
|----------|------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Identifiants PostgreSQL. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Compte admin créé par le seed de `install.sh`, seulement s'il n'existe pas encore (voir « Installer »). |
| `DEFAULT_TIMEZONE` | `Europe/Paris` : fuseau qui découpe les journées. **Copié dans le compte à sa création** (`users.timezone`, lu par `services/daily_rollup.py`) : le changer ensuite dans `.env` n'a aucun effet. |
| `DEFAULT_UNIT_SYSTEM` | `metric` (copié dans le compte à sa création, comme le fuseau). |

### Fichiers

| Variable | Rôle |
|----------|------|
| `MEDIA_DIR` / `EXPORTS_DIR` | Photos, documents, rapports (dans les conteneurs). |
| `MEDIA_ENCRYPTION_KEY` | Chiffrement au repos des fichiers de `MEDIA_DIR` (clé Fernet ; vide = désactivé) : photos, documents médicaux, preuves, ECG, tracés GPS, document CDA. Pas les rapports, les exports, le tampon d'envoi ni la base. **Clé perdue = fichiers chiffrés perdus** : la sauvegarder avec `.env`. |
| `MAX_UPLOAD_MB` | Taille maximale d'une photo (`15`) : corps, repas, aliments. |
| `FOOD_LOOKUP_ONLINE` | `false` (défaut) : le hub ne sort pas sur Internet. `true` : « Code-barres » dans Mes aliments (saisi, ou lu sur une photo quand aucun de vos aliments ne le porte) interroge `OPENFOODFACTS_URL` avec **le code-barres seul** (ni photo, ni compte, ni repas, ni donnée de santé) et reçoit la fiche produit entière (valeurs, ingrédients, Nutri-Score, NOVA, additifs, allergènes…). La lecture du code sur la photo se fait toujours sur le hub, hors ligne, et la photo n'est pas gardée. |
| `OPENFOODFACTS_URL` | `https://world.openfoodfacts.org` (une instance miroir possible). |
| `RETENTION_DAYS` | `0` = tout garder. |

Tailles d'envoi maximales :

| Envoi | Limite |
|-------|--------|
| Toute requête passant par nginx | 25 Mo (`client_max_body_size 25m`, `nginx/default.conf`). |
| `/api/v1/imports/apple-health` | Aucune (envoi en flux, délai 1 h). |
| `/api/v1/sync/auto-export` | Aucune (délai 10 min). |
| Document médical | 25 Mo (`api/v1/medical.py`). |
| Fichier de preuve | 30 Mo côté API, mais nginx refuse d'abord au-delà de 25 Mo. |
| Photo (corps, repas, aliment) | `MAX_UPLOAD_MB` par photo ; une requête (un repas avec plusieurs photos) reste sous les 25 Mo de nginx. |

### IA (Ollama) — un modèle par tâche

| Variable | Recommandé | Utilisé pour |
|----------|-----------|--------------|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Adresse d'Ollama vue depuis Docker. |
| `OLLAMA_VISION_MODEL` | `medgemma1.5` | Photos (face / profil / dos) ; photos d'un repas (aliments, portions, étiquettes visibles) ; photo d'une étiquette nutritionnelle dans Mes aliments. |
| `OLLAMA_DOCUMENT_MODEL` | vide (= modèle de vision) | Lecture des PDF et scans : prises de sang, FibroScan, comptes-rendus, ordonnances. |
| `OLLAMA_TEXT_MODEL` | `medgemma:27b` | Résumé des documents, médicaments et diagnostics lus, **synthèse clinique** des rapports ; pour un repas : aliments, grammes, référence Ciqual de chacun et verdict (score, points à surveiller). |

Utiliser **exactement** le nom affiché par `ollama list`. Détail du
fonctionnement et des limites : [guide IA médicale](ia-medicale.md).
La lecture d'une étiquette tourne **dans l'API**, pas dans le worker
(`services/food_label.py`, 100 s au plus, sinon « Lecture trop longue :
réessayer ») ; les photos, documents et repas sont lus par le worker.
Les valeurs d'un aliment du repas sont calculées par le code depuis la
table Ciqual ou l'étiquette d'un aliment de « Mes aliments » ; à défaut,
c'est l'estimation du modèle, vérifiée (`services/meal_ai.py`).
Changer le modèle de vision rend les anciens scores photo non comparables :
lancer ensuite « Réanalyser tout l'historique ».

### Journaux

| Variable | Rôle |
|----------|------|
| `LOG_LEVEL` | `INFO` (ou `DEBUG` pour diagnostiquer). |
| `LOG_JSON` | `true` : journaux JSON. |

Un jeton passé dans l'URL (`?token=`) est écrit `token=***` dans les
journaux d'accès de l'API et de nginx.

### Interface web et carte des parcours

| Variable | Rôle |
|----------|------|
| `WEB_PORT` | Port de l'interface (`8082`). |
| `VITE_MAP_KEY` | Clé MapTiler gratuite pour le fond de carte (rebuild `web`). |
| `VITE_TILE_URL` / `VITE_TILE_ATTRIB` | Autre fournisseur de tuiles ; `none` = tracé seul. |

### Serveur MCP (optionnel)

| Variable | Rôle |
|----------|------|
| `MCP_BIND` | `127.0.0.1` (défaut) ou `0.0.0.0` pour le réseau local. |
| `MCP_PORT` | `9000` : port publié sur l'hôte (dans le conteneur, le serveur écoute toujours sur 9000). |
| `MCP_TRANSPORT` | `streamable-http` (recommandé : une requête, une réponse JSON — un simple `curl` marche), `sse` ou `stdio`. |
| `PHOENIX_API_TOKEN` | Seulement en `stdio`. En réseau, chaque client envoie son propre jeton `hub:full` : rien de secret dans `.env`. |
| `API_BASE_URL` | Adresse de l'API vue par le serveur MCP (`http://api:8000/api/v1`, posée par compose ; à régler en `stdio` hors Docker). |
| `MCP_HOST` | Adresse d'écoute dans le conteneur (`0.0.0.0` par défaut, `mcp/phoenix_mcp/app.py`). |

Limite connue : le conteneur `mcp` reçoit tout `.env` (`env_file`),
secrets compris, alors qu'il n'en a pas besoin. Détails : [guide MCP](mcp.md).

### Internes (compose, scripts)

Posées par `docker-compose.yml`, les scripts ou un défaut du code : à ne
pas mettre dans `.env` en temps normal.

| Variable | Où | Rôle |
|----------|----|------|
| `DATABASE_URL` | `api`, `worker` | Construite depuis `POSTGRES_*` (`postgresql+asyncpg://…@db:5432/…`). |
| `REDIS_URL` | `api`, `worker` | `redis://redis:6379/0`. |
| `TMPDIR` | `api` | `/data/exports/tmp` : tampon des gros envois, sur le volume `exports` plutôt que dans `/tmp` ; en clair. |
| `UPDATE_DIR` | `api` (défaut du code) | `/data/update`, où compose monte `./run`. |
| `RUN_MIGRATIONS` | `worker` : `false` | `backend/entrypoint.sh` applique les migrations au démarrage sauf si `false` : seule l'API migre. |
| `GIT_COMMIT` | `web` (argument de build), `api`, `worker` | Commit affiché à côté du nom et imprimé dans les rapports ; exporté par `update.sh` et `install.sh`. |
| `COMPOSE` | `update.sh` | Commande compose (défaut `docker compose`). |

## Jetons d'accès (API)

Page **Import › « Jetons d'accès (API) »**. Le secret n'est affiché qu'une
fois ; un jeton se révoque à tout moment.

| Scope | Permet |
|-------|--------|
| `ingest:watch` | Envoyer des relevés montre / Santé (`/ingest/watch`, `/sync/health`, Raccourci). |
| `ingest:ppc` | Envoyer les données de la PPC. |
| `ingest:photo` | Envoyer des photos (`/ingest/photo`). |
| `write:measurements` | Écrire des valeurs, Health Auto Export, import Apple, compteurs, repas, pipi, pointage, prises de médicament. **Modifie** aussi (repas, aliments, sessions de travail) et **supprime par identifiant** : valeurs, repas et leurs photos, aliments et leurs photos, pipis, sessions de travail, prises de médicament. |
| `write:metrics` | Créer / modifier des métriques — **pour l'administrateur seulement** (catalogue partagé) ; refusé (403) au jeton d'un autre compte. |
| `read:all` | **Lire** les données de santé (valeurs, export, rapports, photos…). |
| `hub:full` | Tout ce que fait l'application web (serveur MCP, assistant), sauf gérer les jetons, la 2FA, supprimer le compte, télécharger le Raccourci et `/system/update` (session web uniquement). |

Un jeton qui ne fait qu'envoyer n'a pas besoin de `read:all` — et ne doit
pas l'avoir. Le droit exigé par chaque route est listé dans la
[référence de l'API](../api.md).

**Jeton dans l'URL.** Pour les Raccourcis iPhone, ces routes
(`write:measurements`) acceptent aussi le jeton en `?token=<jeton>` :
`/imports/apple-health`, `/sync/tally`, `/sync/auto-export`, `/meals`,
`/journal/urination`, `/logs/import`, `/work/import`, `/work/clock`,
`/medications/take`, `/treatments/{id}/intakes`, `/foods/scan` (lit
un code-barres, n'enregistre rien), `/stock` (un achat scanné)
(toutes en `POST`).
Les journaux de l'API et de nginx écrivent `token=***`. Une URL peut
tout de même finir dans un proxy ajouté devant, un historique ou un
Raccourci partagé : un tel jeton ne doit porter que `write:measurements`,
et se révoque s'il a fuité. Tous les niveaux d'accès (session, admin,
`hub:full`, scopes) : [SECURITY.md](../../SECURITY.md#access-levels).

## Sauvegarde

Voir la section « Data, backup & restore » du
[README](../../README.md#data-backup--restore) : la base (`pgdata`), les
volumes `media` et `exports`, **et `.env`** — sans `MEDIA_ENCRYPTION_KEY`,
les fichiers chiffrés sont perdus pour de bon ; garder `.env` en lieu sûr.
`run/` et `import/` n'ont pas besoin d'être sauvegardés.
