# Guide — installation, configuration, mise à jour

Tout se règle dans le fichier `.env` à la racine (modèle commenté :
[`.env.example`](../../.env.example)). Après une modification :
`docker compose up -d` (et `--build` si le code a changé).

## Installer

```bash
git clone <ce-dépôt> phoenix-health-hub && cd phoenix-health-hub
./install.sh        # crée .env (SECRET_KEY aléatoire), build, migre, seed, démarre
```

Ouvrir `http://<machine>:8082` (port `WEB_PORT`) et se connecter avec
`ADMIN_EMAIL` / `ADMIN_PASSWORD`.

## Mettre à jour

```bash
git pull
docker compose up -d --build     # les migrations s'appliquent au démarrage de l'API
```

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
| `api` | FastAPI (`/api/v1`), applique les migrations au démarrage. |
| `worker` | Tâches longues : imports Apple, lecture IA des documents, photos, rapports, réconciliation. |
| `web` | Nginx + interface React, port `WEB_PORT`. |
| `mcp` | Serveur MCP (optionnel, profil `mcp`) — voir le [guide MCP](mcp.md). |

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
| `ACCESS_TOKEN_TTL_MIN` | `15` | Durée d'une session avant rafraîchissement. |
| `REFRESH_TOKEN_TTL_DAYS` | `14` | Durée maximale d'une connexion. |
| `JWT_ALGORITHM` | `HS256` | Algorithme de signature. |
| `CORS_ORIGINS` | vide | Origines navigateur autorisées (vide = même origine). |
| `ENV`, `DEBUG`, `APP_NAME`, `API_V1_PREFIX` | | Réglages généraux (laisser tels quels). |
| `MFA_ISSUER` | `Phoenix Health Hub` | Nom affiché dans l'application 2FA (TOTP). |

### Base, compte initial, région

| Variable | Rôle |
|----------|------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Identifiants PostgreSQL. |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Compte créé au premier démarrage. |
| `DEFAULT_TIMEZONE` | `Europe/Paris` : fuseau qui découpe les journées. |
| `DEFAULT_UNIT_SYSTEM` | `metric`. |

### Fichiers

| Variable | Rôle |
|----------|------|
| `MEDIA_DIR` / `EXPORTS_DIR` | Photos, documents, rapports (dans les conteneurs). |
| `MEDIA_ENCRYPTION_KEY` | Chiffrement au repos des fichiers (clé Fernet ; vide = désactivé). |
| `MAX_UPLOAD_MB` | Taille maximale d'une photo (`15`). |
| `RETENTION_DAYS` | `0` = tout garder. |

### IA (Ollama) — un modèle par tâche

| Variable | Recommandé | Utilisé pour |
|----------|-----------|--------------|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Adresse d'Ollama vue depuis Docker. |
| `OLLAMA_VISION_MODEL` | `medgemma1.5` | Photos (face / profil / dos). |
| `OLLAMA_DOCUMENT_MODEL` | vide (= modèle de vision) | Lecture des PDF et scans : prises de sang, FibroScan, comptes-rendus, ordonnances. |
| `OLLAMA_TEXT_MODEL` | `medgemma:27b` | Résumé des documents, médicaments et diagnostics lus, **synthèse clinique** des rapports. |

Utiliser **exactement** le nom affiché par `ollama list`. Détail du
fonctionnement et des limites : [guide IA médicale](ia-medicale.md).
Changer le modèle de vision rend les anciens scores photo non comparables :
lancer ensuite « Réanalyser tout l'historique ».

### Journaux

| Variable | Rôle |
|----------|------|
| `LOG_LEVEL` | `INFO` (ou `DEBUG` pour diagnostiquer). |
| `LOG_JSON` | `true` : journaux JSON. |

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
| `MCP_PORT` | `9000`. |
| `MCP_TRANSPORT` | `streamable-http` (recommandé : une requête, une réponse JSON — un simple `curl` marche), `sse` ou `stdio`. |
| `PHOENIX_API_TOKEN` | Seulement en `stdio`. En réseau, chaque client envoie son propre jeton `hub:full` : rien de secret dans `.env`. |

Détails : [guide MCP](mcp.md).

## Jetons d'accès (API)

Page **Import › « Jetons d'accès (API) »**. Le secret n'est affiché qu'une
fois ; un jeton se révoque à tout moment.

| Scope | Permet |
|-------|--------|
| `ingest:watch` | Envoyer des relevés montre / Santé (`/ingest/watch`, `/sync/health`, Raccourci). |
| `ingest:ppc` | Envoyer les données de la PPC. |
| `ingest:photo` | Envoyer des photos (`/ingest/photo`). |
| `write:measurements` | Écrire des valeurs, Health Auto Export, import Apple, compteurs. |
| `write:metrics` | Créer / modifier des métriques. |
| `read:all` | **Lire** les données de santé (valeurs, export, rapports, photos…). |
| `hub:full` | Tout ce que fait l'application web (serveur MCP, assistant), sauf gérer les jetons, la 2FA et le compte. |

Un jeton qui ne fait qu'envoyer n'a pas besoin de `read:all` — et ne doit
pas l'avoir. Le droit exigé par chaque route est listé dans la
[référence de l'API](../api.md).

## Sauvegarde

Voir la section « Data, backup & restore » du [README](../../README.md).
