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

**La réalité des enseignes (à revérifier enseigne par enseigne avant de
commencer).** À ma connaissance, aucune ne publie d'API ouverte pour
remplir le panier d'un client. Se connecter avec les identifiants du
client, c'est passer par leurs API privées, ce qui :
- va contre la plupart des conditions d'utilisation ;
- peut casser à chaque mise à jour de leur site ;
- se heurte aux protections anti-robot, aux CAPTCHA et à la double
  authentification ;
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
3. **Panier rempli par le hub**, enseigne par enseigne, seulement là où
   une API officielle ou un accès partenaire existe, ou après accord
   explicite de l'utilisateur sur les risques ci-dessus. Le hub remplit
   le panier ; il **ne commande et ne paie jamais** : validation et
   paiement se font sur le site de l'enseigne.

**Les identifiants, s'il faut aller jusqu'à l'étape 3.**
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
  que le mot de passe. Une double authentification est relayée à
  l'utilisateur, jamais contournée.
- L'utilisateur peut les supprimer à tout moment, et ils sont effacés
  avec le compte. Chaque usage est noté dans le journal d'audit, sans le
  secret.
- Tests : isolement entre deux comptes (fixture `member`), et aucun
  secret dans les réponses, les journaux ni les exports.

**Ce qui sort du hub.** Le produit et la quantité, rien d'autre.
- C'est optionnel (à activer par chaque utilisateur) et documenté, selon
  la règle du hub pour tout appel sortant.
- Aucune donnée de santé ne part : ni repas, ni analyses, ni valeurs.
- Un panier révèle quand même des habitudes alimentaires ; l'enseigne
  les voit déjà quand on commande chez elle.

**À décider.**
- Quelles enseignes, en commençant par la tienne.
- Jusqu'où automatiser : liste seule, liste avec liens, ou panier rempli.
- Accepter ou non le risque « conditions d'utilisation » de l'étape 3.

## Sécurité prévue

Listée dans [SECURITY.md](../SECURITY.md#planned-further-hardening) :
- images de conteneur signées et scannées ;
- sauvegardes chiffrées hors site ;
- purge automatique selon `RETENTION_DAYS`.
