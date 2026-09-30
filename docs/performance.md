# Performances — mesures avant / après

Chaque changement fait pour la vitesse est mesuré avant et après, avec
la méthode ci-dessous, et noté ici (règle de [CLAUDE.md](../CLAUDE.md)).

## Méthode

- **Machine de mesure** : conteneur de 4 vCPU (Xeon 2,1 GHz), 15 Go de
  mémoire, PostgreSQL 16, l'API en un seul processus uvicorn, appelée
  directement (sans nginx), cache chaud. Sur ta machine les durées sont
  plus courtes ; ce qui compte est l'écart avant / après.
- **Données factices** : un compte `test.user@example.com`, **2 347 820
  relevés Apple bruts sur 5 ans** (octobre 2021 → septembre 2026 ;
  fréquence cardiaque toutes les 5 min, énergie active toutes les 2 min,
  pas, distance, SpO₂, VFC, poids, nuits par phases… 13 métriques) et
  20 812 valeurs quotidiennes. Aucune donnée réelle.
- **Mesure** : chaque appel seul, trois fois de suite, on garde la
  médiane. Écart d'une mesure à l'autre : ± 10 ms.
- **Mêmes résultats** : avant de garder une optimisation, les réponses
  (vue de chaque métrique sur 30 et 365 jours, récap d'accueil, les
  quatre tableaux de bord) sont enregistrées avec l'ancien code puis
  avec le nouveau : elles doivent être identiques octet pour octet.

## Journal

### 2026-09-30 (2) — toutes les routes, le site, plusieurs utilisateurs

**Données** : le jeu factice couvre maintenant chaque domaine sur 5 ans
— 2 415 530 relevés bruts, 44 016 valeurs quotidiennes, 5 475 repas
analysés, 1 303 pointages, 3 863 preuves et traces, 10 385 prises de
médicaments, 3 000 résultats de labo, 300 ECG, 1 653 séances, 500
tracés GPS, 150 aliments et 3 000 mouvements de stock.

**Méthode** : les 74 routes GET mesurées une à une ; pour chaque route
changée, l'ancien code (commit `a1bdf58`) et le nouveau tournent côte à
côte sur les mêmes données et sont appelés en alternance (9 à 15 appels,
médiane). Les réponses des 72 routes comparables sont identiques octet
pour octet (`/measurements` sans filtre : même contenu, son ordre variait
déjà d'un appel à l'autre).

| Route (page) | Avant | Après |
|---|---:|---:|
| `/work/incomplete` (Travail → « À compléter ») | 1 375 ms | 293 ms |
| `/medications/adherence` (Suivi → observance) | 229 ms | 14 ms |
| `/facts` sur un mois (rapports, MCP) | 289 ms | 34 ms |
| `/facts` sans période | 291 ms | 55 ms |
| `/stock` (Journal → stock) | 427 ms | 210 ms |
| `/summary` (Accueil) | 110 ms | 68 ms |
| `/journal/days` (Journal, un mois) | 35 ms | 24 ms |
| `/sleep/nights` (un mois) | 43 ms | 28 ms |
| `/trends` (courbes par semaine / mois) | 18–28 ms | 10–12 ms |
| Réconciliation complète (Données → Réconcilier, 2,4 M relevés) | 56,2 s | 19,3 s |

Causes et corrections :

1. **« À compléter »** chargeait les nuits de 5 ans (33 451 phases de
   sommeil) pour quelques jours à compléter, relisait les 3 863 preuves
   pour chacun de ces jours et cherchait la métrique « pas » à chaque
   jour. Les nuits sont lues pour les jours à compléter seulement, les
   preuves rangées par jour une fois, la métrique lue une fois.
2. **Observance et `/facts`** chargeaient toutes les prises depuis le
   début : seules celles de la période sont lues, les premières et
   dernières dates sont comptées par PostgreSQL.
3. **Stock** : les repas ne sont plus relus en entier (photos,
   aliments, analyse) mais seulement leurs lignes analysées, et chaque
   aliment ne parcourt que ses propres lignes.
4. **Accueil** : les 17 tuiles sont lues ensemble (5 requêtes au lieu de
   88) ; une page garde en mémoire, le temps de la requête, les métriques
   déjà lues (oubliées si la requête est annulée).
5. **Nuits** : la requête est bornée par l'heure de début (un relevé de
   sommeil ne dure jamais deux jours), l'index la lit directement.
6. **Tendances, première nuit connue** : le jour et la valeur seulement,
   plus les lignes entières.
7. **Réconciliation** : les relevés sont lus par blocs de 20 000 au lieu
   d'un par un (385 000 allers-retours internes pour la seule fréquence
   cardiaque) : fréquence cardiaque 7,7 s → 2,2 s. Reconstruites à neuf
   par l'ancien et le nouveau code, les 44 016 valeurs quotidiennes sont
   identiques (0 ligne de différence).

**Le site (téléphone)** :

| | Avant | Après |
|---|---:|---:|
| Code téléchargé pour ouvrir l'accueil | 1 047 Ko | 185 Ko |
| Tableau de bord nutrition (JSON) | 594 Ko | 45 Ko |
| Preuves, tout l'historique (JSON) | 1,5 Mo | 134 Ko |
| Page de connexion affichée, 4G simulée* | 2,90 s | 0,58 s |
| Tuiles de l'accueil après connexion, 4G simulée* | 1,01 s | 1,07 s |

\* Chromium, 4 Mbit/s, 80 ms de latence, processeur ralenti 4 fois
(un téléphone), cache vide, médiane de 3 chargements.

- nginx compresse le texte (gzip) : rien ne l'était, ni le code de la
  page ni le JSON de l'API. Jamais les réponses qui portent une session
  ou un jeton (connexion, renouvellement, jetons, raccourci) : leur
  taille compressée pourrait trahir un secret (attaque BREACH).
- Chaque page n'est téléchargée qu'à sa première ouverture ; le code de
  l'accueil part dès l'ouverture du site, pendant la connexion. Les
  bibliothèques (React, graphiques, carte) sont à part : après une mise
  à jour du hub, le navigateur ne recharge que le code du hub. Une page
  restée ouverte pendant une mise à jour se recharge une fois (au plus
  une par minute) quand le code d'une page a changé de nom ; vérifié
  avec deux vraies versions A → B, et avec un fichier manquant (un seul
  rechargement, puis le message « Cette page n'a pas pu se charger »).

**Plusieurs utilisateurs** : N personnes ouvrent en même temps l'Accueil
puis Santé (les appels de ton navigateur, en parallèle), 3 fois chacune.
Médiane du temps d'une page :

| Utilisateurs | 2 processus (avant) | 4 processus (défaut) | 8 processus |
|---:|---:|---:|---:|
| 1 | 134 ms | 154 ms | 107 ms |
| 5 | 438 ms | 321 ms | 261 ms |
| 10 | 743 ms | 504 ms | 347 ms |
| 20 | 1 438 ms | 773 ms | 946 ms |

La machine de mesure n'a que 4 cœurs, partagés avec PostgreSQL et le
client : au-delà de 4 processus elle sature. Sur une machine plus
grosse, `API_WORKERS` (un par cœur, 8 au plus avec les 100 connexions
par défaut de PostgreSQL) monte plus haut.

**Le plantage après la mise à jour de 10:06** : la mise à jour a
reconstruit l'API seule ; son nouveau conteneur a reçu une autre adresse
IP, et nginx, qui ne résolvait le nom `api` qu'à son démarrage, a
continué d'appeler l'ancienne adresse (« connect() failed (111:
Connection refused) », 502 partout, la page restait sur « Le hub ne
répond pas… ») jusqu'au redémarrage de `web`. Reproduit à l'identique
en local (l'API change d'adresse, 502 encore 12 s après) ; corrigé :
nginx redemande l'adresse au DNS de Docker toutes les 10 s — même
scénario, la page revient en moins de 10 s.

### 2026-09-30 — des millions de relevés Apple

| Appel (page) | Avant | Après |
|---|---:|---:|
| `/dashboard/activity` (Santé → Activité) | 1 274 ms | 116 ms |
| `/summary` (Accueil, récap du jour) | 614 ms | 118 ms |
| `/dashboard/body` (Santé → Corps) | 580 ms | 80 ms |
| `/dashboard/heart` (Santé → Cœur) | 361 ms | 50 ms |
| `/samples` (Données → « Tout ce qui est enregistré ») | 294 ms | 84 ms |
| `/samples?metric_key=heart.rate` | 93 ms | 79 ms |
| `/catalog/heart.rate/overview` (vue d'une métrique, 365 j) | 62 ms | 18 ms |
| `/catalog/activity.steps/overview` | 55 ms | 14 ms |
| `/data/inventory` (Données → « Ce que contient le hub ») | 336 ms | 341 ms (inchangé, voir plus bas) |

Causes et corrections :

1. **Moyennes glissantes quadratiques** (tableaux de bord, courbes de
   poids et de photos) : pour chaque jour, le calcul relisait toute la
   série — 2 000 jours, 4 millions de comparaisons par métrique. Les
   bornes de la fenêtre sont maintenant trouvées par dichotomie dans les
   jours triés : chaque jour ne lit que ses 7 (ou 30) jours. Mêmes
   nombres : `tests/test_rolling_windows.py` compare au calcul d'avant.
2. **La vue d'une métrique lisait tout l'historique** (accueil, Santé,
   Données, rapports, MCP) : cinq ans de valeurs quotidiennes chargées
   en objets complets pour n'en montrer que 30 jours (19 001 objets pour
   le seul récap d'accueil). Seule la fenêtre affichée est lue ; le
   nombre de jours, la première date et les sources sont comptés par
   PostgreSQL.
3. **Tableaux de bord** : ils lisent le jour et la valeur, plus les
   lignes entières.
4. **Index `(user_id, start_at)` sur les relevés** (migration `0025`) :
   la liste de tous les relevés, triée par date, ne trie plus 2,35
   millions de lignes à chaque page — la requête passe de 359 ms à
   0,3 ms ; le reste des 84 ms est le compte exact du total.

La migration construit l'index au premier démarrage après la mise à
jour : environ 3 s pour 2,35 millions de relevés ; pendant ce temps la
page affiche « Le hub ne répond pas… nouvel essai toutes les 5 s » et
revient seule.

### 2026-09-30 — les pages n'attendent plus derrière une photo

Mesure : un repas envoyé avec 3 photos JPEG de 6 000 × 4 000 px
(19 Mo chacune) à un processus API ; pendant l'envoi, un petit appel
(`/system/version`) toutes les 100 ms. Le plus lent de ces petits
appels :

| | Avant | Après |
|---|---:|---:|
| Petit appel pendant la conversion des photos | 3 650 ms | 22 ms |

Avant, le processus convertissait les photos (et lisait étiquettes,
codes-barres, OCR des documents) lui-même et ne répondait plus à rien ;
ce travail tourne maintenant à part (un thread), l'API continue de
répondre. En production, avec deux processus, une page sur deux tombait
sur le processus occupé : d'où les pages « Chargement… » qui duraient.

## Ce qui reste lent, et pourquoi

- **L'inventaire (≈ 330 ms)** compte exactement chaque relevé par
  métrique et par source : PostgreSQL lit toute la table. Un index
  couvrant `(user_id, metric_id, source, start_at)` a été essayé : pas
  plus rapide (il faut quand même lire 2,35 millions d'entrées) et 8,5 s
  de construction — pas retenu. Piste : une table de comptes tenue à
  jour à chaque écriture de relevés (quelques millisecondes), au prix
  d'un mécanisme de plus à garder juste à chaque import, synchro et
  suppression.
- **Le total de la liste des relevés** (≈ 60 ms) : compté exactement,
  pour la pagination.
- **Les tableaux de bord sur tout l'historique** (≈ 50–200 ms, 5 ans de
  points par métrique) : compressés, ils pèsent 10 fois moins sur le
  réseau.
- **La réconciliation complète** : 19 s pour 2,4 millions de relevés
  (56 s avant). Piste : faire la règle du jour dans PostgreSQL (quelques
  secondes), au prix d'une seconde écriture de cette règle. Elle tourne
  dans le `worker`, pas dans l'API : les pages restent libres.
- **`/measurements` sans aucun filtre** (≈ 1,7 s) : tout l'historique de
  toutes les métriques ; le site filtre toujours, seul un assistant MCP
  appelé sans métrique ni date le demanderait.
- **L'analyse d'un repas** attend la réponse d'Ollama, qui a son propre
  conteneur (et sa carte graphique chez toi) ; l'attente se fait dans le
  `worker`, elle ne ralentit pas les pages.

## nginx : envois et réponses

**Envois** (photos de repas, documents, JSON de Health Auto Export) :
nginx les transmet à l'API au fil de l'eau (`proxy_request_buffering
off`). Avant, tout envoi de plus de 16 Ko était d'abord écrit en entier
dans un fichier temporaire de nginx, non chiffré, puis relu pour l'API —
c'est l'avertissement « a client request body is buffered to a
temporary file » vu sur `POST /api/v1/sync/auto-export`. Vérifié
derrière un nginx 1.24 avec la configuration du dépôt :

| Envoi | Avant | Après |
|---|---|---|
| Health Auto Export, JSON de 650 Ko | fichier temporaire + avertissement | transmis directement, 200 |
| Le même, envoyé par morceaux (« chunked ») | fichier temporaire | transmis directement, 200 |
| Repas avec une photo de 7,9 Mo | fichier temporaire + avertissement | transmis directement, 201, photo relue |
| Envoi de plus de 25 Mo | refusé (413) | refusé (413) |

La taille des envois peut varier librement : rien n'est gardé en
mémoire côté nginx, l'API lit le corps à mesure qu'il arrive.

**Réponses** : `location /api/` garde en mémoire jusqu'à 64 Ko
d'en-têtes (`proxy_buffer_size`) et 32 × 64 Ko = 2 Mo de réponse
(`proxy_buffers`). Une photo de repas affichée (200 Ko à 1 Mo) y tient.

- Les tampons sont pris au besoin (une réponse JSON de 5 Ko en utilise
  un seul) et rendus à la fin de la requête.
- Une réponse de plus de 2 Mo (export, rapport PDF, très grande photo) :
  le surplus part dans un fichier temporaire de nginx, comme avant —
  aucune erreur, aucune coupure.
- Mémoire : au plus ~2 Mo par réponse en cours ; 20 grandes photos
  affichées en même temps ≈ 40 Mo, rendus aussitôt après.
