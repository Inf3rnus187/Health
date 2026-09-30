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

- **L'inventaire (≈ 340 ms)** compte exactement chaque relevé par
  métrique et par source : PostgreSQL lit toute la table. Un index
  couvrant `(user_id, metric_id, source, start_at)` a été essayé : pas
  plus rapide (il faut quand même lire 2,35 millions d'entrées) et 8,5 s
  de construction — pas retenu.
- **Le total de la liste des relevés** (≈ 80 ms) : compté exactement,
  pour la pagination.
- **La reconstruction complète des valeurs quotidiennes** (Données →
  Réconcilier) : 56 s pour 2,35 millions de relevés. Elle tourne dans le
  `worker`, pas dans l'API : les pages restent libres.
- **L'analyse d'un repas** attend la réponse d'Ollama, qui a son propre
  conteneur (et sa carte graphique chez toi) ; l'attente se fait dans le
  `worker`, elle ne ralentit pas les pages.

## nginx : réponses de l'API en mémoire

`location /api/` garde en mémoire jusqu'à 64 Ko d'en-têtes
(`proxy_buffer_size`) et 32 × 64 Ko = 2 Mo de réponse
(`proxy_buffers`). Une photo de repas (200 Ko à 1 Mo) y tient : plus
d'écriture sur le disque ni d'avertissement « buffered to a temporary
file ».

- **Tailles variables** : les tampons sont pris au besoin (une réponse
  JSON de 5 Ko en utilise un seul) et rendus à la fin de la requête.
- **Réponse de plus de 2 Mo** (export, rapport PDF, très grande photo) :
  le surplus part dans un fichier temporaire de nginx, comme avant —
  aucune erreur, aucune coupure, seulement l'avertissement dans le
  journal de `web`.
- **Mémoire** : au plus ~2 Mo par réponse en cours ; 20 grandes photos
  chargées en même temps ≈ 40 Mo, rendus aussitôt après.
- Les envois (photos, exports Apple) ne sont pas concernés : ce réglage
  ne touche que les réponses.
