# Guide — serveur MCP (assistant IA branché sur le hub)

Le serveur MCP donne à un assistant (Claude Desktop, Claude Code, tout
client MCP) **l'accès à tout le hub** : données Apple Santé, Dossier,
Suivi, documents et leur texte, marqueurs, poids, photos, rapports avec
synthèse, automatisations — 53 outils, listés avec leurs paramètres dans
[`mcp-tools.md`](../mcp-tools.md). Chaque outil appelle l'API REST : il voit
exactement ce que voient les pages.

> Ce serveur détient une clé de **tout votre dossier médical**. Gardez-le
> sur la machine ou le réseau local ; pour un accès à distance, passez par
> un VPN (WireGuard, Tailscale…), jamais par un port ouvert sur Internet.

## 1. Créer le jeton API

Site › **Import › « Jetons d'accès (API) »** › cocher **« Accès complet —
MCP / assistant »** (scope `hub:full`) › Créer. Copier le secret (affiché
une seule fois).

Ce jeton peut tout faire **sauf** gérer les jetons, la 2FA et le compte
(réservés à une connexion web).

## 2. Configurer `.env`

```bash
PHOENIX_API_TOKEN=<le jeton hub:full>
MCP_AUTH_TOKEN=<secret généré par : openssl rand -hex 32>
MCP_BIND=127.0.0.1      # 0.0.0.0 pour y accéder depuis un autre appareil du réseau
MCP_PORT=9000
MCP_TRANSPORT=sse       # ou streamable-http
```

`MCP_AUTH_TOKEN` est **obligatoire** en SSE / HTTP : sans lui le serveur
refuse de démarrer, et toute requête sans l'en-tête
`Authorization: Bearer <MCP_AUTH_TOKEN>` reçoit un 401.

## 3. Démarrer

```bash
docker compose --profile mcp up -d --build mcp
docker compose logs mcp --since 5m
```

Vérifier (depuis la machine cliente) :

```bash
curl -i http://<IP>:9000/sse                     # → 401 Unauthorized (normal)
curl -N -H "Authorization: Bearer <MCP_AUTH_TOKEN>" http://<IP>:9000/sse
# → un flux « event: endpoint » : le serveur répond
```

## 4. Brancher un client

Points d'entrée : SSE `http://<IP>:9000/sse`, ou `http://<IP>:9000/mcp` avec
`MCP_TRANSPORT=streamable-http`. En-tête obligatoire :
`Authorization: Bearer <MCP_AUTH_TOKEN>`.

### Claude Code

```bash
claude mcp add --transport sse phoenix http://<IP>:9000/sse \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

### Claude Desktop (via `mcp-remote`)

Dans `claude_desktop_config.json` (Node.js requis) :

```json
{
  "mcpServers": {
    "phoenix": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "http://<IP>:9000/sse",
        "--allow-http",
        "--header", "Authorization:${AUTH_HEADER}"
      ],
      "env": { "AUTH_HEADER": "Bearer <MCP_AUTH_TOKEN>" }
    }
  }
}
```

`--allow-http` n'est nécessaire que pour une adresse en `http://` du
réseau local.

### Sans réseau : stdio

Un client qui lance lui-même le serveur (stdio) n'a besoin ni de port ni de
secret. Sur la machine du hub, depuis le dossier du dépôt :

```bash
docker compose run --rm -T -e MCP_TRANSPORT=stdio mcp
```

Depuis un autre poste, la même commande à travers SSH :

```json
{
  "mcpServers": {
    "phoenix": {
      "command": "ssh",
      "args": ["moi@serveur", "cd /chemin/phoenix-health-hub && docker compose run --rm -T -e MCP_TRANSPORT=stdio mcp"]
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
| Le conteneur `mcp` s'arrête aussitôt | `MCP_AUTH_TOKEN` vide : le définir (ou `MCP_TRANSPORT=stdio`). |
| 401 côté client | En-tête absent ou secret différent de `MCP_AUTH_TOKEN`. |
| Outils en erreur `403: User session or hub:full token required` | `PHOENIX_API_TOKEN` n'a pas le scope `hub:full`. |
| Outils en erreur `401` de l'API | Jeton révoqué / mal copié : en créer un nouveau. |
| Injoignable depuis un autre appareil | `MCP_BIND=0.0.0.0`, puis `docker compose --profile mcp up -d mcp`. |
