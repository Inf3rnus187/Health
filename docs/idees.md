# Idées et travaux à venir

Ce qui n'est pas encore commencé, au même endroit : le besoin, ce qui
reste à décider, et comment le faire proprement. Une entrée terminée part
dans le [CHANGELOG](../CHANGELOG.md) et sort d'ici. Les phases déjà
livrées sont dans la [feuille de route](architecture.md#roadmap).

## En attente d'une décision

### Poids unitaire stable d'un repas à l'autre

Deux repas identiques analysés à quelques minutes d'écart peuvent donner
des grammes un peu différents : pour « 2 œufs », l'IA estime un œuf à
50 g une fois, 60 g la suivante. Deux options :

- **reprendre automatiquement** le premier poids trouvé pour cet aliment ;
- un bouton **« Garder ce poids »** qui l'enregistre dans la fiche de
  « Mes aliments » (le code fait déjà « nombre × poids de la fiche »
  quand la fiche en a un).

### Réconciliation calculée dans PostgreSQL

Aujourd'hui : 11,9 s pour 2,4 millions de relevés, dans le worker, sans
bloquer les pages ([performance](performance.md)). Descendre à quelques
secondes demande de ranger les relevés par jour dans PostgreSQL : le
découpage en jours locaux, la conversion des unités (dont « 0,97 →
97 % ») et le calcul par source existeraient alors **en deux copies**,
Python (synchros, tests) et SQL, qui finiraient par diverger. Pas fait
tant que ce risque n'est pas accepté.

## Idées

### Paniers drive préparés quand le stock baisse

**Le besoin.** Quand un aliment de « Mes aliments » passe sous un seuil,
le hub prépare le panier de courses chez l'enseigne drive de chaque
utilisateur (Leclerc Drive, Carrefour, Auchan, Intermarché, Courses U…).

**Ce que le hub sait déjà.**
- Le stock de chaque aliment : achats, pertes, comptages, et ce que les
  repas analysés en ont pris (`services/stock_level.py`).
- Le code-barres (EAN) de chaque fiche et sa page Open Food Facts : de
  quoi retrouver le même produit chez une enseigne.
- Il manque un **seuil** par aliment : il n'existe pas encore.

**La réalité des enseignes.** Aucune enseigne ne publie d'API ouverte
pour remplir le panier d'un client ; les projets de la communauté
(références plus bas) le confirment et passent tous par le site privé
de l'enseigne. Seule piste officielle : Intermarché (Les Mousquetaires)
a un portail développeurs, qu'il reste à lire. Passer par le site privé
avec la session du client :
- va contre la plupart des conditions d'utilisation ;
- peut casser à chaque mise à jour du site (un vérificateur Auchan est
  mort avec le nouveau site en 2023, un serveur MCP Carrefour a été
  archivé en 2026) ;
- se heurte à l'anti-robot DataDome (Leclerc, Auchan) : seul un vrai
  navigateur Chrome passe, et des appels en rafale (5 ajouts au panier
  en parallèle) se font bloquer ; il faut un appel à la fois, à rythme
  humain ;
- peut faire bloquer le compte client.

**Le plan, par étapes (chacune utile seule).**

1. **Seuil et liste de courses, sans rien envoyer dehors.**
   - Un seuil par aliment (« en racheter sous 2 boîtes »).
   - Une page « Liste de courses » : ce qui est sous son seuil, la
     quantité pour revenir au niveau voulu, avec code-barres et marque.
   - Export texte et partage depuis l'iPhone.
   - L'outil MCP « que dois-je racheter ? ».
2. **Liens vers l'enseigne choisie (au choix de chaque utilisateur).**
   Chaque ligne ouvre la recherche de l'enseigne par code-barres ou par
   nom ; l'utilisateur ajoute au panier sur le site. Le lien part de
   son navigateur, pas du hub ; il ne porte que le produit.
3. **Panier rempli par l'assistant, sur l'ordinateur de l'utilisateur
   (la voie à privilégier).** Des serveurs MCP existent déjà pour
   Leclerc, Auchan, Intermarché et Carrefour (références plus bas). Ils
   tournent sur l'ordinateur de l'utilisateur et remplissent le panier
   dans son propre navigateur Chrome, où il est déjà connecté.
   L'assistant (Claude Desktop…) est branché sur le MCP du hub et sur
   celui de l'enseigne : il lit la liste de courses dans le hub, puis
   remplit le panier. Le hub n'envoie rien dehors et ne garde **aucun
   identifiant**. Il suffit de rendre la liste lisible par l'assistant,
   avec le code-barres, la marque, la quantité et le produit déjà acheté
   chez cette enseigne s'il est connu. Le guide MCP dira comment
   brancher les deux.
4. **Panier rempli par le hub lui-même**, seulement là où une API
   officielle ou un accès partenaire existe (portail Intermarché à
   étudier), ou après accord explicite de l'utilisateur sur les risques
   ci-dessus. Sans API officielle, cela demanderait un navigateur Chrome
   dans un conteneur du hub, avec la session de chaque utilisateur :
   c'est plus exposé à DataDome depuis un serveur, et une session vaut
   un mot de passe.

Dans tous les cas, **ni commande ni paiement automatiques** : aucun des
outils existants ne le fait, et le hub non plus. La validation et le
paiement se font sur le site de l'enseigne.

**Les identifiants, s'il faut aller jusqu'à l'étape 4.**
- Chaque utilisateur saisit les siens, pour lui seul. On ne les
  enregistre que depuis une session web : pas de jeton API ni d'accès
  MCP, comme pour la gestion des jetons.
- Ils sont chiffrés au repos, avec une clé dédiée
  (`DRIVE_CREDENTIALS_KEY`) documentée dans `.env.example`,
  `configuration.md` et `SECURITY.md`.
- Ils ne ressortent jamais : ni dans une réponse de l'API (elle dit
  seulement « enregistré le … »), ni dans un journal, un export, un
  rapport ou un outil MCP.
- Quand l'enseigne le permet, le hub garde un jeton de session plutôt
  que le mot de passe ; un cookie de session se protège comme un mot de
  passe. Une double authentification est relayée à l'utilisateur,
  jamais contournée.
- L'utilisateur peut les supprimer à tout moment, et ils sont effacés
  avec le compte. Chaque usage est noté dans le journal d'audit, sans le
  secret.
- Tests : isolement entre deux comptes (fixture `member`), et aucun
  secret dans les réponses, les journaux ni les exports.

**Ce qui sort du hub.** Aux étapes 1 à 3, rien : la liste reste dans le
hub, et c'est le navigateur ou l'assistant de l'utilisateur qui parle à
l'enseigne. À l'étape 4, le produit et la quantité, rien d'autre.
- C'est optionnel (à activer par chaque utilisateur) et documenté, selon
  la règle du hub pour tout appel sortant.
- Aucune donnée de santé ne part : ni repas, ni analyses, ni valeurs.
- Un panier révèle quand même des habitudes alimentaires ; l'enseigne
  les voit déjà quand on commande chez elle.

**À décider.**
- Quelles enseignes, en commençant par la tienne.
- Jusqu'où automatiser : liste seule, liste avec liens, panier rempli par
  l'assistant (étape 3), ou par le hub (étape 4).
- Accepter ou non le risque « conditions d'utilisation » des étapes 3
  et 4.

**Références** (lues le 30/09/2026 ; certains sites n'étaient pas
lisibles depuis l'environnement de travail et restent à lire).

| Enseigne | Lien | Ce qu'il montre |
|---|---|---|
| Leclerc | [skunkobi/mcp-leclerc-drive](https://github.com/skunkobi/mcp-leclerc-drive/tree/main) | Serveur MCP en TypeScript (licence MIT, v0.3). Outils : magasins, recherche, ajout, retrait, quantité, lecture du panier. Pas de commande ni de créneau. Connexion faite une fois dans un vrai Chrome, dont le profil est gardé en local : aucun identifiant stocké. Non officiel. |
| Leclerc | [docs/api-capture.md](https://github.com/skunkobi/mcp-leclerc-drive/blob/main/docs/api-capture.md) | Les appels du site : la recherche (page HTML), un seul point d'entrée pour ajouter, modifier ou retirer (quantité 0), le panier lu dans les pages, et un localisateur de magasins en JSON. Session par cookies, protégée par DataDome : il faut un vrai Chrome, un appel à la fois. |
| Leclerc | [lobehub : skunkobi-mcp-leclerc-drive](https://lobehub.com/mcp/skunkobi-mcp-leclerc-drive) | Fiche du même serveur dans un annuaire MCP (non lue d'ici). |
| Carrefour | [maximeallanic/mcp-carrefour-drive](https://github.com/maximeallanic/mcp-carrefour-drive) · [fiche lobehub](https://lobehub.com/mcp/maximeallanic-mcp-carrefour-drive) | Serveur MCP (Playwright, Chrome sans fenêtre) : connexion, magasin, recherche, fiche produit (nutrition, ingrédients, allergènes), panier, créneaux. Pas de paiement. E-mail et mot de passe passés en variables d'environnement. **Archivé en août 2026.** Il le dit : Carrefour n'a pas d'API publique. |
| Carrefour | [azerpas/carrefour-drive-monitor](https://github.com/azerpas/carrefour-drive-monitor/tree/master) · [README](https://github.com/azerpas/carrefour-drive-monitor/blob/master/README.md) | Surveillance des drives et de leurs disponibilités par code postal (Python, né pendant le COVID). Pas de panier, peu maintenu. |
| Intermarché | [developers.intermarche.com](https://developers.intermarche.com/) · [portail Mousquetaires (recette)](https://api-data-developer-portal.qa.mousquetaires.com/) | Portails développeurs du groupe : **la seule piste officielle**. Ce qu'ils ouvrent (catalogue, magasins, panier ?) et à qui (public ou partenaires) reste à lire : non lisibles d'ici. |
| Intermarché | [nicolasestrem/mcp-intermarche-drive](https://glama.ai/mcp/servers/nicolasestrem/mcp-intermarche-drive) ([source](https://github.com/nicolasestrem/mcp-intermarche-drive)) | Serveur MCP (TypeScript, MIT) : recherche, lecture du panier, ajout, quantité, retrait, substitutions. Pas de commande. Il utilise l'onglet Chrome où l'utilisateur est connecté, sans jamais exporter les cookies. API privée non documentée, vérifiée en juillet 2026. N'utilise pas le portail officiel. |
| Auchan | [MrRaph/mcp-auchan-drive](https://github.com/MrRaph/mcp-auchan-drive) | Serveur MCP (TypeScript, MIT, actif) : recherche, promotions, panier, magasins, fidélité, commandes passées, favoris. Il reprend la session du navigateur installé (Chrome, Firefox) ou une variable `AUCHAN_COOKIE`. API privée, ralentie volontairement contre DataDome. « Usage personnel uniquement ». |
| Auchan | [nlevee/go-auchan-drive-checker](https://github.com/nlevee/go-auchan-drive-checker) | Vérificateur de créneaux (Go). **Archivé en 2023** : hors service depuis le nouveau site. Exemple de la fragilité. |
| Toutes | [r/developpeurs : « Drive APIs »](https://www.reddit.com/r/developpeurs/comments/1ay1qcl/drive_apis/) | Discussion sur les API des drives français (non lisible d'ici). |

## Sécurité prévue

Listée dans [SECURITY.md](../SECURITY.md#planned-further-hardening) :
- images de conteneur signées et scannées ;
- sauvegardes chiffrées hors site ;
- purge automatique selon `RETENTION_DAYS`.
