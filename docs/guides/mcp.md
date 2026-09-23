# Guide — serveur MCP (assistant IA branché sur le hub)

Le serveur MCP donne à un assistant (Claude Desktop, Claude Code, tout
client MCP) **l'accès à tout le hub** : données Apple Santé, Dossier,
Suivi, documents et leur texte, marqueurs, poids, photos, rapports avec
synthèse, automatisations — 62 outils, listés avec leurs paramètres dans
[`mcp-tools.md`](../mcp-tools.md). Chaque outil appelle l'API REST : il voit
exactement ce que voient les pages.

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
faire **sauf** gérer les jetons, la 2FA et le compte.

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
- **Agir** : saisir une valeur, créer une métrique, déclarer / modifier une
  maladie ou un traitement, ajouter un rendez-vous, envoyer un document puis
  le faire lire, relancer une lecture IA, réconcilier les données, générer
  un rapport (synthèse clinique), lancer une automatisation.
- **Tout le reste** : `api_get` / `api_call` atteignent n'importe quelle
  route de la [référence API](../api.md). Les routes destructrices agissent
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
| `502 API unreachable` | Le conteneur `mcp` ne joint pas l'API : `docker compose ps`, `docker compose logs mcp`. |
| Injoignable depuis un autre appareil | `MCP_BIND=0.0.0.0`, puis `docker compose --profile mcp up -d mcp`. |
