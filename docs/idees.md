# Idées et travaux à venir

Ce qui n'est pas encore commencé, au même endroit : le besoin, ce qui
reste à décider, et comment le faire proprement. Une entrée terminée part
dans le [CHANGELOG](../CHANGELOG.md) et sort d'ici. Les phases déjà
livrées sont dans la [feuille de route](architecture.md#roadmap).

## Décidé, rien à coder

### Réconciliation calculée dans PostgreSQL : écartée (30/09/2026)

**L'idée.** Ranger les relevés par jour dans PostgreSQL pour passer la
réconciliation complète de 12 à 20 s (2 M relevés, 60 métriques chez
l'utilisateur) à quelques secondes (estimation, non mesurée).

**Pourquoi c'est écarté.** Aujourd'hui il n'existe **qu'une copie** de
la règle du jour (`daily_rollup.rebuild`) : la réconciliation, la synchro
iPhone, Health Auto Export et une saisie à la main l'appellent toutes.
Un même jour ne peut donc pas avoir deux valeurs selon le chemin. La
version SQL créerait une deuxième copie (découpage en jours locaux avec
le fuseau, conversions d'unités dont « 0,97 → 97 % », calcul par
source), gardée en Python pour les synchros et les tests : deux copies
finissent par diverger. Le gain (quelques secondes sur une opération
rare, en arrière-plan) ne vaut pas ce risque. Règle retenue : les
performances s'améliorent sans rien casser ni ajouter de risque.

**Ce qui a été fait à la place.** La réconciliation se relance seule une
fois après chaque mise à jour du hub qui touche le serveur, et son
journal donne sa durée et ses métriques les plus longues (`seconds`,
`slowest`) pour voir où part le temps sur de vraies données. Puis elle a
été répartie sur plusieurs cœurs (`RECONCILE_PARALLEL`, 4 par défaut),
avec la même fonction : 10 s → 5 s sur la machine de mesure, jours
identiques octet pour octet ([performance](performance.md)).

### Poids unitaire d'un repas à l'autre (décidé le 30/09/2026)

**Le constat.** Sans poids écrit, le poids d'une unité (une tomate, un
concombre) est estimé par l'IA et change d'un repas à l'autre : deux
tomates comptées 2 × 125 g un jour, 2 × 150 g un autre ; un demi
concombre 75 g ou 150 g.

**Les options écartées.**
- Retenir la première estimation : stable mais au hasard.
- Un bouton « Garder ce poids » : une fiche au poids moyen fixe, stable
  mais pas le poids du jour.

**Décision : l'utilisateur écrit le poids pesé dans la description**
(`2 tomates 240 g`, `2 tomates (240 g)`, `240 g de tomates`,
`tomates : 240 g`). Le hub le garde tel quel (« écrits par toi ») :
c'est déjà le cas, vérifié sur ces quatre tournures. Les légumes
varient trop d'une pièce à l'autre pour un poids fixe.

## Idées

### Paniers drive remplis par le hub quand le stock baisse

**Statut : noté pour plus tard, pas commencé.** Première enseigne :
**Leclerc** (décidé le 30/09/2026). La recherche et la réflexion
ci-dessous sont faites : repartir d'ici, sans les refaire.

**Ce qui est décidé.**
- Le hub **crée et remplit le panier** chez l'enseigne drive de chaque
  utilisateur, rien de plus. **La commande et le paiement se font
  toujours par l'utilisateur, dans la vraie appli de son magasin.**
  Aucune route, aucun outil, aucune ligne de code ne commande ni ne paie.
- **Le hub le fait tout seul**, par une tâche planifiée du worker : il
  regarde le stock et ajoute au panier ce qui manque, quand il le faut.
- **Le MCP du hub reçoit les outils du panier.** L'assistant de
  l'utilisateur, qui parle au hub par ce MCP, peut ainsi lire la liste
  de courses, chercher un produit, ajouter, retirer ou vider le panier.
- **Chaque utilisateur saisit ses identifiants** de son enseigne dans le
  hub ; le hub les garde et s'en sert proprement (règles plus bas).

**Ce que le hub sait déjà.**
- Le stock de chaque aliment : achats, pertes, comptages, et ce que les
  repas analysés en ont pris (`services/stock_level.py`).
- Le code-barres (EAN) de chaque fiche et sa page Open Food Facts : de
  quoi retrouver le même produit chez l'enseigne.
- Il manque un **seuil** par aliment : il n'existe pas encore.

**Ce qu'il faut construire.**

1. **Seuil et liste de courses.**
   - Un seuil par aliment (« en racheter sous 2 boîtes ») et la quantité
     visée (« remonter à 6 »).
   - Une page « Liste de courses » : ce qui est sous son seuil et
     combien en racheter.
   - La même liste dans l'API et le MCP.
2. **Le drive de chaque utilisateur** (page Compte → « Mon drive ») :
   - l'enseigne, le magasin et les identifiants ;
   - un bouton « Tester la connexion » ;
   - l'interrupteur « Remplir le panier tout seul » ;
   - l'heure de passage.
3. **Le produit de l'enseigne pour chaque fiche.**
   - Il est trouvé par le code-barres, sinon par le nom ; l'utilisateur
     le confirme une fois et le hub le retient pour la suite.
   - Un produit introuvable ou en rupture est signalé, jamais remplacé
     sans son accord.
4. **La tâche planifiée** (worker, horaire réglable dans `.env` et par
   utilisateur), pour chaque utilisateur qui l'a activée :
   - calculer la liste ;
   - **lire d'abord le panier** et n'ajouter que la différence (pas de
     double ajout d'un passage à l'autre, ni par-dessus un ajout fait à
     la main) ;
   - noter ce qui a été ajouté, ce qui a échoué et pourquoi, dans un
     journal visible sur la page et lisible par le MCP.
5. **Les outils MCP du hub** (et les routes de l'API qui vont avec) :
   - `shopping_list` : la liste de courses ;
   - `drive_search` : chercher un produit chez l'enseigne ;
   - `drive_cart` : lire le panier ;
   - `drive_add_to_cart`, `drive_update_quantity`, `drive_remove_from_cart`,
     `drive_clear_cart` : le modifier ;
   - `drive_fill_cart` : remplir le panier depuis la liste, maintenant ;
   - `drive_history` : le journal des passages.

   Aucun outil ne commande ni ne paie, et aucun ne lit les identifiants.
6. **Un module par enseigne**, derrière la même interface (chercher, lire
   le panier, ajouter, changer la quantité, retirer). On commence par
   l'enseigne de l'utilisateur.
   - Là où une API officielle existe (portail Intermarché à étudier), on
     l'utilise.
   - Sinon, on fait comme les projets de la communauté : la session de
     l'utilisateur dans un vrai Chrome, tenu par un conteneur dédié du
     hub, un appel à la fois, à rythme humain (DataDome).

**Ce que la recherche a appris (30/09/2026, liens plus bas).**
- **Aucune enseigne ne publie d'API ouverte** pour remplir le panier
  d'un client. Carrefour le dit lui-même dans son projet MCP.
- **Tous les projets de la communauté passent par le site privé** de
  l'enseigne, avec la session du client, pilotée dans un vrai Chrome
  (par CDP ou Playwright). Serveurs MCP existants : Leclerc (v0.3),
  Auchan (actif), Intermarché (débutant), Carrefour (archivé).
- **Aucun ne commande ni ne paie** : ils s'arrêtent au panier, comme le
  hub.
- **Anti-robot DataDome** (Leclerc, Auchan) : seul un vrai Chrome passe,
  un appel à la fois, à rythme humain. Cinq ajouts au panier lancés en
  même temps se font bloquer.
- **Ces outils cassent souvent** : un vérificateur Auchan est mort avec
  le nouveau site en 2023, le serveur MCP Carrefour a été archivé en
  août 2026.
- **Seule piste officielle : Intermarché** (Les Mousquetaires), qui a
  deux portails développeurs. Ce qu'ils ouvrent (catalogue, magasins,
  panier ?) et à qui (public ou partenaires) reste à lire : ces sites,
  lobehub, glama et Reddit n'étaient pas lisibles depuis
  l'environnement de travail.
- **Façons de garder la session**, vues dans ces projets :
  - Leclerc : connexion faite une fois dans un vrai Chrome dont le
    profil est gardé ;
  - Auchan : cookies lus dans le navigateur installé, ou une variable
    d'environnement ;
  - Intermarché : l'onglet où l'utilisateur est connecté, sans exporter
    les cookies ;
  - Carrefour : e-mail et mot de passe en variables d'environnement.

  Le hub, lui, gardera identifiants et session chiffrés, par
  utilisateur (règles plus bas).

**Leclerc, par où commencer** (d'après
[api-capture.md](https://github.com/skunkobi/mcp-leclerc-drive/blob/main/docs/api-capture.md)
et [mcp-leclerc-drive](https://github.com/skunkobi/mcp-leclerc-drive/tree/main)).
- **Les appels du site.**
  - La recherche de produits renvoie une page HTML, à lire.
  - Un seul point d'entrée modifie le panier : ajouter, changer la
    quantité, retirer (quantité 0).
  - Le panier se lit dans les pages du magasin ; il n'a pas de point
    d'entrée à lui.
  - Les magasins se trouvent par une API JSON (autocomplétion, magasins
    proches).
- **La session** tient par des cookies, protégés par DataDome. Le
  projet passe par un vrai Chrome (CDP) qui porte les cookies,
  l'empreinte du navigateur et les défis résolus.
- **Le rythme** : un appel à la fois, avec une pause entre deux ; jamais
  en parallèle.
- **Ce que le projet fait** : magasins, recherche, ajout, retrait,
  quantité, lecture du panier. Pas de créneau ni de commande, ce qui
  correspond au périmètre du hub. Licence MIT : on peut s'en inspirer
  en le citant.
- **Premier essai à faire**, avant d'écrire le module du hub : Chrome
  dans un conteneur du hub, connexion avec un compte de test, puis
  recherche, ajout et lecture du panier à rythme humain. On vérifie que
  DataDome laisse passer depuis le serveur, et combien de temps la
  session tient.

**Points techniques à régler (d'après les références).**
- DataDome repère plus facilement un Chrome qui tourne sur un serveur
  sans écran. À tester avec l'enseigne choisie avant de s'engager.
- La première connexion peut demander un CAPTCHA ou un code reçu par
  SMS ou e-mail : l'utilisateur le saisit une fois dans la page « Mon
  drive », puis le hub garde la session.
- Le site d'une enseigne change sans prévenir. Chaque module a ses tests
  sur des réponses enregistrées. Un échec de passage est signalé dans le
  journal, sans rien casser dans le reste du hub.

**Les identifiants.**
- Chaque utilisateur saisit les siens, pour lui seul. On ne les
  enregistre que depuis une session web : pas de jeton API ni d'accès
  MCP, comme pour la gestion des jetons.
- Ils sont chiffrés au repos, avec une clé dédiée
  (`DRIVE_CREDENTIALS_KEY`) documentée dans `.env.example`,
  `configuration.md` et `SECURITY.md`. La session gardée (cookies) est
  chiffrée de la même façon, car elle vaut un mot de passe.
- Ils ne ressortent jamais : ni dans une réponse de l'API (elle dit
  seulement « enregistré le … »), ni dans un journal, un export, un
  rapport ou un outil MCP.
- Une double authentification est relayée à l'utilisateur, jamais
  contournée.
- L'utilisateur peut les supprimer à tout moment, et ils sont effacés
  avec le compte. Chaque usage est noté dans le journal d'audit, sans le
  secret.
- Tests : isolement entre deux comptes (fixture `member`), aucun secret
  dans les réponses, les journaux ni les exports, et aucun chemin de
  commande ou de paiement.

**Ce qui sort du hub.**
- Vers l'enseigne choisie, et seulement si l'utilisateur a activé son
  drive : ses identifiants, les produits cherchés et les quantités du
  panier.
- Aucune donnée de santé : ni repas, ni analyses, ni valeurs.
- C'est un appel sortant du hub, donc documenté dans `SECURITY.md` et
  `configuration.md`, selon la règle du hub.
- Le panier révèle des habitudes alimentaires ; l'enseigne les voit déjà
  quand on commande chez elle.
- Les risques (conditions d'utilisation de l'enseigne, compte bloqué)
  sont expliqués sur la page « Mon drive » avant d'activer.

**Reste à choisir, au moment de s'y mettre.** Le magasin Leclerc de
chaque utilisateur, qui se choisit dans la page « Mon drive ».

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
