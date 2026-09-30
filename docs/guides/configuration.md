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

**Pendant la mise à jour.** L'API redémarre quelques secondes (après
chaque mise à jour qui la touche). Une page ouverte à ce moment-là
affiche « Le hub ne répond pas (redémarrage après une mise à jour ?) —
nouvel essai toutes les 5 s… » et revient seule, **toujours connectée** :
seule une session refusée par le hub (jeton révoqué, 14 jours sans
visite) ramène à la page de connexion. Une mise à jour qui ajoute un
index sur les relevés le construit au démarrage : quelques secondes de
plus (≈ 3 s pour 2,35 millions de relevés, migration `0025`).

Quand une mise à jour ne reconstruit que l'API, son nouveau conteneur
reçoit une autre adresse sur le réseau Docker : nginx redemande
l'adresse de `api` au DNS de Docker toutes les 10 s (`resolver
127.0.0.11` dans `nginx/default.conf.template`), la page revient donc seule.
Avant, nginx gardait l'adresse lue à son démarrage et répondait 502
(« connect() failed (111: Connection refused) ») jusqu'à `docker compose
restart web`.

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

**La version installée** s'affiche à droite du nom, en haut de chaque
page : « v838aeb9 · 25/09 10:09 » — le commit de la dernière mise à jour
terminée par l'hôte et son heure (sur téléphone, le commit seul), le même
que « ✓ À jour (838aeb9) » du bandeau (`GET /system/version`, pour tout
compte connecté). Une mise à jour qui ne touche que le serveur ne
reconstruit pas la page : le survol du numéro donne aussi la version de
la page chargée (« page chargée : v9fed481, construite le … »). Sans
`update.sh` (construction à la main), c'est le commit de l'API, sinon
celui de la page.
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
| `api` | FastAPI (`/api/v1`), applique les migrations au démarrage ; lit `run/` (état des mises à jour). Appelle aussi Ollama : lecture d'une étiquette nutritionnelle (Mes aliments) et, quand la file (Redis) est indisponible, rapport construit sur place, synthèse clinique comprise. `API_WORKERS` processus (4 par défaut) répondent en même temps, chacun avec au plus `DB_POOL_SIZE` + `DB_MAX_OVERFLOW` connexions à PostgreSQL (10 par défaut). |
| `worker` | Tâches longues : imports Apple, lecture IA des documents, des photos et des repas, rapports, réconciliation. |
| `web` | Nginx + interface React, port `WEB_PORT` ; compresse le texte envoyé (gzip), sauf les réponses qui portent une session ou un jeton. Sa configuration (`nginx/default.conf.template`) est remplie au démarrage par les variables `WEB_…` (« Serveur web » plus bas). |
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
docker compose logs api --since 1h | grep slow   # requêtes d'1 s ou plus
docker compose ps
```

Chaque requête de l'API a sa ligne, heure UTC comme nginx, client (celui
que nginx a vu), requête, code, **durée** : `2026-09-30 05:37:56 +0000
192.168.1.250 "GET /api/v1/meals?start=… HTTP/1.0" 200 45 ms` ; une
requête d'une seconde ou plus finit par `slow`. Les lignes de nginx
(`web`) finissent par `rt=` (durée totale, en secondes) et `api=` (durée
de l'API ; `-` pour une page ou un fichier servi par nginx seul) : une
page lente avec un `api=` court vient du réseau ou du navigateur, un
`api=` long de l'API.

Ce que tu envoies au hub (photos de repas, documents, JSON de Health
Auto Export) passe directement de nginx à l'API, au fil de l'eau
(`proxy_request_buffering off` dans `nginx/default.conf.template`) : plus de
fichier temporaire sur le disque de nginx ni d'avertissement « a client
request body is buffered to a temporary file ». La limite de 25 Mo par
requête reste. Dans l'autre sens, nginx garde en mémoire une réponse de
l'API jusqu'à 2 Mo (32 × 64 Ko, `proxy_buffers`), pris au besoin et
rendus à la fin de la requête ; une réponse plus grande (export,
rapport PDF) déborde dans un fichier temporaire comme avant, sans
erreur. Les mesures avant / après de chaque optimisation sont dans
[performance.md](../performance.md).

## Variables d'environnement

### Cœur et sécurité

| Variable | Défaut | Rôle |
|----------|--------|------|
| `SECRET_KEY` | — (obligatoire, ≥ 32 car.) | Signe les sessions (JWT). Générée par `install.sh`. |
| `ACCESS_TOKEN_TTL_MIN` | `15` | Durée du jeton d'accès. La page web le renouvelle seule (`WEB_RENEW_MARGIN_S` avant la fin, 3 min par défaut, et à la première réponse 401) avec le jeton de rafraîchissement : une page restée ouverte ne se déconnecte pas. |
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
| — (pas de variable) | Les repères officiels d'un repas (UE, ANSES, OMS) sont dans le code, hors ligne. Les liens « Comprendre ces références » (Santé.fr, Open Food Facts, ciqual.anses.fr, EUR-Lex, ANSES, OMS) ne sont jamais appelés par le hub : le navigateur les ouvre à la demande, dans un nouvel onglet, sans référent ; un lien produit ne porte que son code-barres. |
| `MEAL_ANALYSIS_MAX_DELAY_MIN` | `60` : délai maximal, en minutes, qu'un envoi de repas peut demander avant son analyse IA (`POST /meals` `analysis_delay_min`, outil MCP `log_meal`). |
| `FOOD_REFRESH_DAYS` | `30` (défaut) : chaque nuit (`FOOD_REFRESH_HOUR`:`FOOD_REFRESH_MINUTE` UTC, 4 h 40 par défaut), le worker relit la page Open Food Facts des fiches qui ont un code-barres et n'ont pas été relues depuis ce nombre de jours (`FOOD_REFRESH_PER_NIGHT` au plus par nuit, 50 par défaut, `FOOD_REFRESH_PAUSE_S` d'écart ; seul le code-barres sort). `0` : jamais. Sans effet si `FOOD_LOOKUP_ONLINE=false`. Les boutons « ↻ Open Food Facts » et « Tout relire » restent disponibles. |
| `OPENFOODFACTS_URL` | `https://world.openfoodfacts.org` (une instance miroir possible). |
| `RETENTION_DAYS` | `0` = tout garder. |

Tailles d'envoi maximales :

| Envoi | Limite |
|-------|--------|
| Toute requête passant par nginx | `WEB_MAX_BODY_MB` (32 Mo). |
| `/api/v1/imports/apple-health` | Aucune (envoi en flux, délai `WEB_IMPORT_TIMEOUT_S`, 1 h). |
| `/api/v1/sync/auto-export` | Aucune (délai `WEB_SYNC_TIMEOUT_S`, 10 min). |
| Document médical | `MEDICAL_MAX_MB` (25 Mo). |
| Fichier de preuve | `EVIDENCE_MAX_MB` (30 Mo). nginx s'arrêtait avant, à 25 Mo : `WEB_MAX_BODY_MB` vaut désormais 32 pour laisser passer une preuve de 30 Mo. |
| Photo (corps, repas, aliment) | `MAX_UPLOAD_MB` par photo ; une requête (un repas avec plusieurs photos) reste sous `WEB_MAX_BODY_MB`. |

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
(`services/food_label.py`, `LABEL_AI_TIME_LIMIT_S` au plus, 100 s par
défaut, sinon « Lecture trop longue : réessayer ») ; les photos, documents et repas sont lus par le worker.
Les valeurs d'un aliment du repas sont calculées par le code depuis la
table Ciqual ou l'étiquette d'un aliment de « Mes aliments » ; à défaut,
c'est l'estimation du modèle, vérifiée (`services/meal_ai.py`).
Changer le modèle de vision rend les anciens scores photo non comparables :
lancer ensuite « Réanalyser tout l'historique ».

### Journaux

| Variable | Rôle |
|----------|------|
| `LOG_LEVEL` | `INFO` (ou `DEBUG` pour diagnostiquer). |
| `LOG_JSON` | `true` : les messages des services en JSON (heure dans le champ `timestamp`) ; `false` : les mêmes, lisibles. La ligne d'accès (`app.access`) et les autres restent en texte, précédées de l'heure UTC. |

Un jeton passé dans l'URL (`?token=`) est écrit `token=***` dans les
journaux d'accès de l'API et de nginx. Chaque ligne de l'API porte son
heure UTC (en tête, ou dans le champ `timestamp` d'une ligne JSON) ; la
ligne d'accès (`app.access`) donne l'adresse du client transmise par
nginx (`X-Real-IP`) et la durée de la requête.

### Interface web et carte des parcours

| Variable | Rôle |
|----------|------|
| `WEB_PORT` | Port de l'interface (`8082`). |
| `API_WORKERS` | Processus de l'API (`4`). Environ un par cœur ; 8 au plus avec les 100 connexions par défaut de PostgreSQL (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW` par processus, 10 par défaut, plus celles du `worker`). Mesures : [performance.md](../performance.md). |
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

### Réglages de fonctionnement (rien n'est fixé dans le code)

Tout ce qui dimensionne, cadence ou limite le hub se règle dans `.env` :
processus, connexions, délais, tailles, lots, budgets de l'IA, règles de
calcul, rythmes de la page web. Les défauts ci-dessous sont les valeurs
d'avant ; une variable absente de `.env` garde son défaut. Après une
modification : `docker compose up -d` (compose recrée les services dont
la configuration a changé ; pas besoin de reconstruire les images).
Source : `backend/app/core/tuning.py` (API et worker),
`nginx/default.conf.template` et `docker-compose.yml` (serveur web et
gunicorn). Une valeur hors bornes (négative, heure `9pm`…) empêche l'API
de démarrer, avec le nom de la variable dans le journal.

Ce qui reste dans le code, volontairement : les constantes physiques et
de format (1 g de sel = 400 mg de sodium, un mille = 1,609 km, une date
`AAAAMMJJ` de 8 caractères), les réglages internes des lecteurs de
fichiers (longueur minimale d'un mot reconnu…), la mise en page (tailles
des graphiques, nombre de lignes affichées dans une carte) et les repères
officiels d'un repas (UE, ANSES, OMS), qui sont des sources, pas des
réglages.

#### Base de données et tâches de fond

| Variable | Défaut | Rôle |
|----------|--------|------|
| `DB_POOL_SIZE` | `5` | Connexions PostgreSQL gardées ouvertes par processus (API ou worker). |
| `DB_MAX_OVERFLOW` | `5` | Connexions en plus pendant un pic, par processus. Total ≈ (`API_WORKERS` + 1) × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) : rester sous les 100 connexions de PostgreSQL. |
| `DB_POOL_TIMEOUT_S` | `30` | Attente d'une connexion libre avant l'erreur. |
| `WORKER_MAX_JOBS` | `10` | Tâches de fond menées en même temps par le worker. |
| `WORKER_JOB_TIMEOUT_S` | `7200` | Durée maximale d'une tâche (un gros import Apple). |
| `WORKER_MAX_TRIES` | `1` | Essais d'une tâche (`1` : pas de reprise automatique). |
| `WORKER_KEEP_RESULT_S` | `3600` | Durée pendant laquelle Redis garde le résultat d'une tâche. |

#### Serveur API (gunicorn, `docker-compose.yml`)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `API_WORKERS` | `4` | Processus qui répondent en même temps (voir « Interface web »). |
| `API_TIMEOUT_S` | `30` | Un processus qui ne donne plus signe de vie depuis ce temps est redémarré. Une requête longue (un rapport) ne le rend pas muet : les processus sont asynchrones. |
| `API_GRACEFUL_S` | `30` | À l'arrêt (une mise à jour), temps laissé aux requêtes en cours pour finir. |
| `API_KEEPALIVE_S` | `2` | Temps pendant lequel une connexion reste ouverte entre deux requêtes. |

#### Serveur web (nginx, `nginx/default.conf.template`)

Remplies au démarrage du conteneur `web` (seules les variables `WEB_…`
sont remplacées ; défauts dans `nginx/Dockerfile` et `docker-compose.yml`).

| Variable | Défaut | Rôle |
|----------|--------|------|
| `WEB_MAX_BODY_MB` | `32` | Taille maximale d'une requête (un repas et toutes ses photos ensemble). Garder ≥ `EVIDENCE_MAX_MB` et `MEDICAL_MAX_MB`. L'import Apple et Health Auto Export n'ont pas de limite. |
| `WEB_API_TIMEOUT_S` | `120` | Attente de la réponse de l'API. |
| `WEB_SYNC_TIMEOUT_S` | `600` | Idem pour Health Auto Export (`/sync/auto-export`). |
| `WEB_IMPORT_TIMEOUT_S` | `3600` | Idem pour l'envoi d'un export Apple (`/imports/apple-health`). |
| `WEB_GZIP_LEVEL` | `5` | Compression, de `1` (rapide) à `9` (plus petit). |
| `WEB_GZIP_MIN_BYTES` | `1024` | Une réponse plus petite part non compressée. |
| `WEB_DNS_TTL_S` | `10` | nginx redemande l'adresse de l'API à Docker à cet intervalle (une API reconstruite change d'adresse). |
| `WEB_PROXY_BUFFER_KB` | `64` | Taille d'un tampon de réponse. |
| `WEB_PROXY_BUFFERS` | `32` | Nombre de tampons : `WEB_PROXY_BUFFERS` × `WEB_PROXY_BUFFER_KB` (2 Mo) restent en mémoire, au-delà la réponse passe par un fichier temporaire. |
| `WEB_PROXY_BUSY_KB` | `128` | Part des tampons en cours d'envoi au navigateur : ≥ `WEB_PROXY_BUFFER_KB` et < (`WEB_PROXY_BUFFERS` − 1) × `WEB_PROXY_BUFFER_KB`, sinon nginx refuse de démarrer. |
| `WEB_ASSETS_CACHE_DAYS` | `30` | Durée de cache des fichiers du site dans le navigateur (leurs noms changent à chaque version). |

#### Page web (lus par la page avant son affichage)

La page les demande à `GET /api/v1/system/settings` (sans connexion : ni
secret ni donnée d'un compte). Hub injoignable : elle prend les défauts.

| Variable | Défaut | Rôle |
|----------|--------|------|
| `WEB_RETRY_S` | `5` | Pendant un redémarrage du hub, la page réessaie à cet intervalle, sans déconnecter. |
| `WEB_RENEW_MARGIN_S` | `180` | La session est renouvelée ce temps avant la fin du jeton d'accès (`ACCESS_TOKEN_TTL_MIN`) : toutes les 12 min par défaut, jamais plus d'une fois par 30 s. |
| `WEB_REFRESH_TIMEOUT_S` | `15` | Attente d'un renouvellement avant de juger le hub injoignable. |
| `WEB_UPDATE_CHECK_S` | `300` | Recherche d'une nouvelle version installée (et à chaque retour sur l'onglet). |
| `WEB_UPDATE_LOOK_S` | `20` | La même, pendant une mise à jour lancée depuis la page. |
| `WEB_UPDATE_STATE_S` | `15` | État de la mise à jour (administrateur) pendant qu'elle tourne. |
| `WEB_UPDATE_RECENT_S` | `1800` | Une mise à jour finie depuis moins longtemps est confirmée (« ✓ … installée »). |
| `WEB_POLL_S` | `5` | Une lecture IA en cours (repas, document) est regardée à cet intervalle. |
| `WEB_RECONCILE_REFRESH_S` / `WEB_RECONCILE_REFRESH_STEPS` | `10` / `18` | Après « Réconcilier » (Données), les pages sont rafraîchies à cet intervalle, ce nombre de fois (3 min). |
| `WEB_REANALYSIS_REFRESH_S` / `WEB_REANALYSIS_REFRESH_STEPS` | `10` / `12` | Idem après « Réanalyser tout l'historique » (photos). |
| `WEB_PHOTO_REFRESH_S` | `1.5,4,8,13` | Après « Réanalyser » une photo, elle est relue après ces délais (secondes, séparés par des virgules). |
| `WEB_RELOAD_GUARD_S` | `60` | Une page absente après une mise à jour recharge le site au plus une fois dans ce délai, puis affiche l'erreur. |
| `WEB_PAGE_SIZES` | `10,25,50,100,200` | Choix « Par page » des listes. |

La page reçoit aussi, de la même route, le nombre de photos d'un repas
(`MEAL_MAX_PHOTOS` + 1), le délai d'analyse maximal
(`MEAL_ANALYSIS_MAX_DELAY_MIN`) et le maximum hebdomadaire tracé sur le
graphique du travail (`WORK_MAX_WEEK_HOURS`).

#### IA (Ollama)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `OLLAMA_TIMEOUT_S` | `600` | Attente d'une réponse d'Ollama. |
| `OLLAMA_CONCURRENCY` | `1` | Appels au modèle en même temps, par processus (Ollama met les autres en file). |
| `MEAL_AI_TIME_LIMIT_S` | `900` | Durée maximale de l'analyse d'un repas (au-delà : « échec », à relancer). |
| `MEAL_AI_MAX_TOKENS` / `MEAL_AI_JUDGE_TOKENS` | `1500` / `700` | Longueur maximale de la lecture du repas, puis de son verdict. |
| `DOCUMENT_AI_TIME_LIMIT_S` | `1800` | Durée maximale de la lecture d'un document médical. |
| `DOCUMENT_AI_CHUNK_CHARS` / `DOCUMENT_AI_MAX_CHUNKS` | `5000` / `8` | Un long document est lu par morceaux de cette taille, ce nombre au plus. |
| `DOCUMENT_AI_VALUES_TOKENS` / `DOCUMENT_AI_SUMMARY_TOKENS` | `1024` / `900` | Longueur maximale des valeurs lues, puis du résumé. |
| `DOCUMENT_AI_SUMMARY_CHARS` | `12000` | Caractères du document donnés au modèle pour le résumé. |
| `DOCUMENT_AI_REJECTED_MAX` | `30` | Valeurs du modèle écartées (absentes du texte) gardées pour être montrées. |
| `LABEL_AI_TIME_LIMIT_S` | `100` | Durée maximale de la lecture d'une étiquette (Mes aliments). |
| `OCR_MAX_PAGES` / `OCR_DPI` | `12` / `200` | Pages d'un scan lues, et leur résolution. |
| `MEAL_REMARK_MAX_CHARS` | `300` | Une remarque du modèle plus longue est coupée à la fin d'une phrase. |
| `MEAL_INGREDIENTS_MAX_CHARS` | `400` | Une liste d'ingrédients plus longue n'est pas donnée au modèle (il ne l'invente pas). |
| `IMAGE_READ_SIDE` | `2048` | Plus grand côté (pixels) d'une image lue : étiquette, photo ajoutée à un repas. |
| `BARCODE_READ_SIDE` | `2400` | Idem pour un code-barres (barres fines). |
| `PHOTO_COMPARE_SIDE` | `640` | Idem pour deux photos comparées côte à côte. |

#### Tailles et limites

| Variable | Défaut | Rôle |
|----------|--------|------|
| `EVIDENCE_MAX_MB` | `30` | Fichier de preuve. |
| `MEDICAL_MAX_MB` | `25` | Document médical. |
| `IMAGE_MAX_SIDE` | `1280` | Plus grand côté (pixels) d'une photo gardée. |
| `MEAL_MAX_PHOTOS` | `6` | Photos ajoutées à la première d'un repas (7 en tout). |
| `MEAL_MAX_FOODS` | `20` | Lignes « aliment » d'un repas. |
| `MEAL_DESCRIPTION_MAX` | `2000` | Caractères de la description d'un repas. |
| `MEAL_LINE_MAX_G` | `1500` | Une ligne de repas au-delà est refusée comme impossible (grammes). |
| `ECG_MAX_POINTS` / `ROUTE_MAX_POINTS` | `5000` / `3000` | Points d'un ECG ou d'un tracé GPS envoyés à la page (réduits au-delà, l'original reste entier). |
| `DOCUMENT_TEXT_MAX` | `200000` | Caractères du texte d'un document renvoyés par l'API. |

#### Open Food Facts (si `FOOD_LOOKUP_ONLINE=true`)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `OPENFOODFACTS_TIMEOUT_S` | `10` | Attente d'Open Food Facts. |
| `FOOD_REFRESH_HOUR` / `FOOD_REFRESH_MINUTE` | `4` / `40` | Heure (UTC) de la relecture de nuit. |
| `FOOD_REFRESH_PER_NIGHT` | `50` | Fiches relues par nuit. |
| `FOOD_REFRESH_PAUSE_S` | `1` | Écart entre deux fiches. |
| `FOOD_REFRESH_BUDGET_S` | `60` | « Tout relire » répond dans ce délai ; la nuit reprend le reste. |

#### Lots (imports, synchros, recalculs)

Plus grand : moins d'allers-retours avec la base, plus de mémoire.

| Variable | Défaut | Rôle |
|----------|--------|------|
| `IMPORT_BATCH` | `5000` | Lignes écrites d'un coup par un import. |
| `IMPORT_COMMIT_EVERY` | `50000` | Un import Apple enregistre sa progression tous les N relevés. |
| `IMPORT_ROLLUP_BATCH` / `IMPORT_OBS_BATCH` | `500` / `1000` | Jours recalculés, observations cliniques écrites par lot. |
| `ROLLUP_READ_BLOCK` | `20000` | Relevés lus par bloc pour recalculer les valeurs du jour. |
| `SYNC_CHUNK` / `SYNC_ROLLUP_CHUNK` | `2000` / `400` | Lignes écrites, jours recalculés par lot pendant une synchro. |
| `CATALOG_SYNC_BATCH` | `5000` | Lignes par lot quand le catalogue des métriques change. |
| `DELETE_CHUNK` | `500` | Éléments supprimés par lot (suppression en masse). |
| `SQL_IN_CHUNK` | `500` | Identifiants par requête `IN (…)` (900 au plus). |
| `UPLOAD_CHUNK_KB` | `1024` | Morceaux d'écriture d'un gros envoi sur le disque. |
| `IMPORT_REPORT_LINES` | `50` | Lignes listées dans le compte rendu d'un import (lignes ignorées, périodes). |
| `CHAT_TRACE_MAX_CHARS` | `8000` | Caractères d'une trace tirée d'une conversation exportée. |
| `TRACE_SAME_TIME_S` | `60` | Deux traces aussi proches sont la même (pas de doublon). |

#### Mémoire

| Variable | Défaut | Rôle |
|----------|--------|------|
| `GC_FREEZE` | `true` | Une fois l'API (ou le worker) démarrée, ses objets permanents (routes, schémas, tables) sont mis à l'écart du ramasse-miettes de Python : il ne les reparcourt plus à chaque passe (80 à 110 ms de moins sur un grand tableau de bord, [performance](../performance.md)). Rien de ce qu'une requête crée n'est gardé plus longtemps. `false` : comportement standard de Python. |

#### Journaux et mises à jour

| Variable | Défaut | Rôle |
|----------|--------|------|
| `LOG_SLOW_MS` | `1000` | Une requête de l'API au moins aussi longue finit par `slow` dans le journal. |
| `UPDATE_FRESH_S` | `180` | Le cron de `update.sh` est « actif » s'il est passé depuis moins longtemps. |
| `UPDATE_TAKEN_S` | `180` | Une demande « Installer » non prise en charge dans ce délai est signalée. |
| `UPDATE_RUNNING_S` | `1200` | Une mise à jour « en cours » depuis plus longtemps est considérée comme arrêtée. |

#### Travail, sommeil, médicaments, photos, dépenses

| Variable | Défaut | Rôle |
|----------|--------|------|
| `WORK_MAX_DAY_HOURS` / `WORK_MAX_WEEK_HOURS` | `10` / `48` | Maxima du Code du travail : jour, semaine (comptes, rouge du graphique, textes des rapports). |
| `WORK_MAX_SPREAD_HOURS` | `13` | Amplitude maximale d'une journée. |
| `WORK_MIN_REST_HOURS` | `11` | Repos quotidien minimal. |
| `WORK_LONG_SESSION_HOURS` | `12` | Une session aussi longue est signalée. |
| `WORK_MAX_AVG_HOURS` / `WORK_AVG_WEEKS` | `44` / `12` | Moyenne hebdomadaire maximale, sur ce nombre de semaines. |
| `WORK_NIGHT_START` / `WORK_NIGHT_END` | `21:00` / `06:00` | Heures de nuit (heure locale, `HH:MM`). |
| `WORK_MAX_SESSION_HOURS` | `72` | Une session plus longue est refusée comme erreur de saisie. |
| `WORK_OPEN_SESSION_HOURS` | `16` | Une embauche sans débauche vaut « au travail » ce temps. |
| `WORK_PAIR_MAX_HOURS` | `20` | À l'import, une embauche et une débauche plus éloignées ne sont pas appariées. |
| `WORK_PAIR_SEARCH_HOURS` | `20` | L'autre bout d'une session est cherché aussi loin. |
| `WORK_TICKET_MAX_HOURS` | `12` | Un temps de ticket supérieur n'est pas cru. |
| `WORK_CHART_WEEKS` | `52` | Semaines du graphique du rapport de travail. |
| `WORK_HIGHLIGHT_DAYS` | `20` | « Journées les plus significatives » listées. |
| `WORK_CONTINUOUS_HOURS` | `24` | Une session aussi longue est « nuit comprise ». |
| `WORK_STAY_HOURS` | `6` | Une trace aussi longue (parking, hôtel) marque aussi les jours suivants. |
| `WORK_MORNING_HOUR` | `12` | Une débauche manquante est aussi cherchée dans les traces du lendemain avant cette heure (un taxi à 3 h 47). |
| `WORK_CORR_MIN_PAIRS` | `5` | Jours nécessaires à une corrélation (dossier travail ↔ santé). |
| `SLEEP_MANUAL_MAX_HOURS` | `20` | Nuit saisie à la main la plus longue. |
| `SLEEP_AWAKENING_MIN` / `SLEEP_BLOCK_GAP_MIN` | `5` / `60` | Une interruption aussi longue est un réveil ; un écart aussi long commence un autre bloc de sommeil. |
| `SLEEP_SAMPLE_MAX_HOURS` | `48` | Durée maximale d'un relevé de sommeil (borne de recherche). |
| `MEDICATION_FUTURE_MIN` | `10` | Une prise peut être notée jusqu'à ce délai dans le futur (décalage d'horloge). |
| `MEDICATION_LATE_ENTRY_MIN` | `60` | Une prise notée plus tard que ça après l'heure réelle est « saisie tardive ». |
| `ADHERENCE_DAYS` | `30` | Jours couverts par l'observance quand aucune période n'est donnée. |
| `PHOTO_MIN_SIDE` | `300` | Une photo plus petite (pixels) est refusée. |
| `PHOTO_DARK` / `PHOTO_BRIGHT` / `PHOTO_BLURRY` | `35` / `235` / `12` | Luminosité moyenne (0-255) en dessous ou au-dessus de laquelle une photo est refusée ; netteté sous laquelle elle est floue. |
| `PHOTO_TREND_MIN_DAYS` / `PHOTO_TREND_MIN_SPAN_DAYS` | `8` / `21` | Une tendance des photos demande ce nombre de jours, sur au moins cette durée. |
| `PHOTO_TREND_WINDOW_DAYS` / `PHOTO_TREND_SMOOTH_DAYS` | `90` / `7` | Pente lue sur les derniers jours ; lissage sur ce nombre de jours. |
| `PHOTO_TREND_STABLE` | `0.5` | Sous cette pente (points par 30 jours), la tendance est « stable ». |
| `SPENDING_TOP` | `10` | Établissements listés dans Dépenses. |
| `SPENDING_LATE_FROM_HOUR` / `SPENDING_LATE_UNTIL_HOUR` | `21` / `5` | Commandes « tardives » : de cette heure à celle-là (heure locale ; la plage peut passer minuit ou non). |

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
| `write:measurements` | Écrire des valeurs, Health Auto Export, **app iPhone (HealthKit)** — `POST /sync/healthkit`, jeton dans l'en-tête `Authorization` uniquement —, import Apple, compteurs, repas, pipi, pointage, prises de médicament. **Modifie** aussi (repas, aliments, sessions de travail) et **supprime par identifiant** : valeurs, repas et leurs photos, aliments et leurs photos, pipis, sessions de travail, prises de médicament. |
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
