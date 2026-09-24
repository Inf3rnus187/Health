# Guide — serveur MCP (assistant IA branché sur le hub)

Le serveur MCP donne à un assistant (Claude Desktop, Claude Code, tout
client MCP) **l'accès à tout le hub** : données Apple Santé, Dossier,
Suivi, documents et leur texte, marqueurs, poids, photos, Journal (pipi,
repas), aliments et table Ciqual, médicaments et observance, rapports
avec synthèse et vérification, automatisations, heures de travail,
dossier travail et santé — **105 outils**, listés avec leurs paramètres
dans [`mcp-tools.md`](../mcp-tools.md) (généré depuis le serveur). Chaque
outil appelle l'API REST : il voit exactement ce que voient les pages.

> Ce serveur détient une clé de **tout votre dossier médical**. Gardez-le
> sur la machine ou le réseau local ; pour un accès à distance, passez par
> un VPN (WireGuard, Tailscale…), jamais par un port ouvert sur Internet.

## 1. Créer le jeton (le seul secret)

Site › **Import › « Jetons d'accès (API) »** › cocher **« Accès complet —
MCP / assistant »** (scope `hub:full`) › Créer. Copier le jeton (affiché
une seule fois). C'est lui que le client MCP envoie ; il n'y a **rien de
secret à mettre dans `.env`**.

Le serveur MCP vérifie ce jeton auprès de l'API à chaque connexion (401 si
inconnu ou révoqué, 403 s'il n'a pas `hub:full`) puis appelle l'API avec
lui : chaque utilisateur du hub ne voit que ses données, et **révoquer le
jeton coupe l'accès** (effectif en une minute au plus). Ce jeton peut tout
faire **sauf** :

- gérer les jetons, la 2FA et le compte (session du site seulement) ;
- lancer ou suivre une **mise à jour du hub** (`/system/update`) : réservé
  à la session de l'administrateur, jamais à un jeton ;
- modifier le **catalogue des métriques**, partagé par tous les
  utilisateurs : `create_metric` / `update_metric` répondent `403`
  (« administrator only ») si le compte du jeton n'est pas
  l'administrateur (rôle `admin`).

## 2. Configurer `.env` (facultatif)

```bash
MCP_BIND=127.0.0.1               # 0.0.0.0 pour y accéder depuis un autre appareil du réseau
MCP_PORT=9000                    # port publié sur la machine
MCP_TRANSPORT=streamable-http    # recommandé ; ou sse
```

## 3. Démarrer

```bash
docker compose --profile mcp up -d --build mcp
docker compose logs mcp --since 5m
```

Vérifier depuis la machine cliente (mode `streamable-http` : un seul
`curl` par appel, réponse JSON directe) :

```bash
TOKEN='<jeton hub:full>'
# lister les outils
curl -s http://<IP>:9000/mcp -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# lire le poids
curl -s http://<IP>:9000/mcp -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"metric_overview","arguments":{"key":"body.weight","days":30}}}'
```

En mode `sse`, les réponses arrivent dans le flux `/sse` ouvert à part :
`curl` ne suffit plus, il faut un client MCP.

## 4. Brancher un client

Points d'entrée : `http://<IP>:9000/mcp` (`MCP_TRANSPORT=streamable-http`)
ou `http://<IP>:9000/sse` (`MCP_TRANSPORT=sse`). En-tête :
`Authorization: Bearer <jeton hub:full>`.

### Claude Code

```bash
claude mcp add --transport http phoenix http://<IP>:9000/mcp \
  --header "Authorization: Bearer <jeton hub:full>"
# en mode sse : --transport sse … http://<IP>:9000/sse
```

### Claude Desktop (via `mcp-remote`)

Dans `claude_desktop_config.json` (Node.js requis) :

```json
{
  "mcpServers": {
    "phoenix": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "http://<IP>:9000/mcp",
        "--allow-http",
        "--header", "Authorization:${AUTH_HEADER}"
      ],
      "env": { "AUTH_HEADER": "Bearer <jeton hub:full>" }
    }
  }
}
```

`--allow-http` n'est nécessaire que pour une adresse en `http://` du
réseau local.

### Sans réseau : stdio

Un client qui lance lui-même le serveur (stdio) n'a pas besoin de port.
Pas d'en-tête HTTP en stdio : le jeton se passe en variable. Sur la
machine du hub, depuis le dossier du dépôt :

```bash
docker compose run --rm -T -e MCP_TRANSPORT=stdio -e PHOENIX_API_TOKEN=<jeton hub:full> mcp
```

Depuis un autre poste, la même commande à travers SSH :

```json
{
  "mcpServers": {
    "phoenix": {
      "command": "ssh",
      "args": ["moi@serveur", "cd /chemin/phoenix-health-hub && docker compose run --rm -T -e MCP_TRANSPORT=stdio -e PHOENIX_API_TOKEN=<jeton hub:full> mcp"]
    }
  }
}
```

## 5. Ce que l'assistant peut faire

- **Lire** : accueil, toute métrique (vue d'ensemble, valeurs, relevés
  bruts, tendances), inventaire des sources, Dossier (résultats, suggestions,
  chronologie), Suivi, documents et **le texte lu par l'IA**, marqueurs,
  poids, photos, séances / ECG / parcours, rapports et synthèses.
- **Agir** : saisir une valeur, créer une métrique (administrateur
  seulement, voir plus haut), déclarer / modifier une
  maladie ou un traitement, ajouter un rendez-vous, envoyer un document puis
  le faire lire, relancer une lecture IA, réconcilier les données, générer
  un rapport (synthèse clinique), lancer une automatisation.
- **Compter / saisir sans rien effacer** : « ajoute une clope », « un café
  de plus » → `add_to_counter`, qui **ajoute** au total du jour et répond
  le total avant et après (montant négatif pour retirer une erreur,
  jamais sous 0 ; montant `0` : « aucune cigarette aujourd'hui », la
  journée est confirmée à zéro au lieu de rester sans donnée ; il passe
  par `/sync/tally`). `record_measurement` **remplace** la valeur du jour
  (poids, sommeil…) : s'il y en a déjà une différente, il refuse tant que
  l'utilisateur n'a pas confirmé la nouvelle valeur (`replace=true`).
- **Heures de travail** : « j'embauche », « je débauche » (`clock_in` /
  `clock_out`), « combien d'heures sup ce mois-ci ? » (`work_stats`),
  « importe ce fichier de pointages » (`import_work_log` : il lit d'abord
  et montre ce qu'il a compris, puis importe après accord), export CSV ou
  rapport PDF (`generate_report("work")`).
- **Dossier travail et santé** : « importe mes fichiers Embauche et
  Débauche » (`import_logs`, lecture d'abord), « j'étais en arrêt du 12 au
  21 janvier pour épuisement » (`save_absence`), « ajoute cette capture :
  12 appels du chef le 18 » (`add_evidence`), « la montre était déchargée
  cette nuit, je me suis couché à 1 h, levé à 6 h, réveillé 3 fois »
  (`add_sleep_night`), « Uber Eats hier à 21 h 15, burger frites 24,90 € »
  (`add_evidence` type `livraison` avec le repas), « importe mon export
  Uber » (`import_traces` : aussi notes de frais Lucca en PDF, tickets
  NinjaOne, conversations WhatsApp), « importe mes absences Lucca »
  (`import_absences`, lecture d'abord), « mes nuits du mois »
  (`sleep_nights`), « quel lien entre mes heures et mon sommeil ? »
  (`work_health`), rapport complet (`generate_report("work_health")`).
- **Corriger les sessions de travail** : les journées à compléter avec
  leurs indices (`work_incomplete`), ajouter ou corriger une session, sur
  place ou à distance (`save_work_session`), réunir une embauche seule et
  une débauche seule (`merge_work_sessions`), une ligne par jour
  (`work_days`), export texte par session, jour, semaine ou mois en CSV
  ou JSON (`export_work`).
- **Journal et repas** : le journal jour par jour (`journal_days`), un
  pipi maintenant ou à une heure donnée (`log_urination`,
  `list_urinations`, `delete_urination`), « note mon déjeuner : … »
  (`log_meal` : description, type, heure, `photo_base64` pour l'assiette,
  `more_photos_base64` jusqu'à 6 photos de l'emballage, `foods` de « Mes
  aliments » avec leurs grammes), corriger un repas après coup
  (`update_meal`, `foods` remplace la liste), `add_meal_photo`,
  `delete_meal_photo`, `analyze_meal`, `delete_meal` ; « combien m'ont
  coûté les Uber Eats cette année ? » (`meal_spending`).
- **Mes aliments** : `list_foods`, `save_food` (valeurs pour 100 g,
  autres noms, poids du paquet, **unité** `unit_name` / `unit_g`,
  source, code-barres), `search_ciqual` (table Ciqual 2025, hors ligne),
  `lookup_barcode` (Open Food Facts, seulement si
  `FOOD_LOOKUP_ONLINE=true`), `read_food_label` (lit l'étiquette : une
  proposition, rien n'est enregistré), `add_food_photo`, `delete_food`.
- **Médicaments** : « j'ai pris ma paroxétine » (`log_medication`, par
  le nom ; `status` `skipped` = non pris), `medications_today`,
  `medication_intakes` (chaque prise avec heure de prise, heure de
  saisie et canal), `medication_adherence` (observance par traitement),
  `delete_medication_intake`. Une prise notée par MCP garde le canal
  `mcp`.
- **Rapports qui prouvent** : `period_facts` (les faits d'une période
  comme le rapport les prouve : jours saisis / sans donnée, avant /
  après une date, observance, repas, traçabilité des saisies),
  `verify_report` (ce fichier est-il un de mes rapports, intact ?
  SHA-256).
- **Photos, données** : relancer l'analyse d'une photo (`analyze_photo`)
  ou de tout l'historique après un changement de modèle
  (`reanalyze_all_photos`) ; exporter les données en texte CSV, JSON ou
  FHIR (`export_data`).
- **Supprimer en lot** : `delete_many` (preuves et traces — avec les
  repas créés par les livraisons si `meals` —, sessions, absences, repas
  ou rendez-vous ; 5 000 au plus), après avoir montré la liste et obtenu
  l'accord.
- **Tout le reste** : `api_get` / `api_call` appellent une route de la
  [référence API](../api.md) par son **chemin relatif** à `/api/v1`
  (`/metrics/body.weight`, `/events`) — jamais une URL complète
  (`https://…`, `//hôte/…`) ni un segment `..` : c'est refusé avant tout
  envoi, pour que le jeton ne parte jamais vers un autre hôte. Les routes
  réservées ci-dessus restent refusées. Les routes destructrices agissent
  sur de vraies données : l'assistant doit demander confirmation.

Exemples de demandes : « Résume mon dossier et l'évolution de mon HbA1c »,
« Vérifie que la valeur de CAP du FibroScan correspond au document »
(`document_text` + `medical_record`), « Ajoute le traitement proposé par
l'ordonnance », « Génère une synthèse clinique et montre-moi les phrases
retirées ».

## Dépannage

| Symptôme | Action |
|----------|--------|
| `401 Unauthorized` | En-tête absent, jeton mal copié ou révoqué : en créer un nouveau. |
| `403 Forbidden: the token needs the hub:full scope` | Le jeton n'a pas « Accès complet — MCP / assistant ». |
| `403 … administrator only` (`create_metric`, `update_metric`) | Le catalogue des métriques est partagé : réservé au compte administrateur. |
| `403 User session required` (`/system/update`, jetons, 2FA, compte) | Route du site seulement : aucun jeton ne l'atteint. |
| `an API path is expected` (`api_get`, `api_call`) | Donner un chemin relatif à `/api/v1` (`/metrics`), pas une URL. |
| `502 API unreachable` | Le conteneur `mcp` ne joint pas l'API : `docker compose ps`, `docker compose logs mcp`. |
| Une valeur a été remplacée par erreur | Chaque valeur remplacée reste dans le journal d'audit (champs `replaced` / `previous`) : `docker compose exec db psql -U phoenix phoenix -c "select created_at, payload from audit_log where entity = 'measurement' order by created_at desc limit 20"` (`POSTGRES_USER` / `POSTGRES_DB` de `.env`), puis remettre la bonne valeur. |
| Injoignable depuis un autre appareil | `MCP_BIND=0.0.0.0`, puis `docker compose --profile mcp up -d mcp`. |
