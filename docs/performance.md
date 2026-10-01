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

### 2026-10-01 (16) — la machine d'abord ; le ramasse-miettes dans la trace

**Une synchro lente peut venir de l'hôte, pas du hub.** Chez
l'utilisateur, toutes les étapes étaient 10 à 20 fois plus lentes que
sur le banc, y compris `validate` (du Python pur). Mesures sur l'hôte
(commandes en lecture seule, ci-dessous) : processeur 2,4 fois plus
lent par cœur (le calcul de référence en 1,24–1,41 s contre 0,51–0,56 s
ici), et surtout **mémoire saturée** — 61 Go utilisés sur 62, 1,5 Go
disponible, swap plein. Un autre service, sans limite mémoire, en
occupait 24 Go. Une fois redémarré (27 Go disponibles), même code :
synchro habituelle **266 → 110 ms** (`token` 22 → 7, `statistics`
57 → 20, `days` 48 → 19, `commit` 8 → 5 ms) ; la première après un
redémarrage de l'API reste plus longue (650 ms : connexions et plans
neufs).

À vérifier avant de chercher dans le code :

```bash
./version.sh
docker compose exec -T api python -c "import time;t=time.perf_counter();sum(i*i for i in range(10**7));print(round(time.perf_counter()-t,2),'s')"
free -h; vmstat 1 5        # disponible, swap ; si/so ≠ 0 : la machine échange
docker stats --no-stream --format "{{.MemPerc}}\t{{.MemUsage}}\t{{.Name}}" | LC_ALL=C sort -rn | head -8
docker compose exec db psql -U phoenix phoenix -c "select round(100.0*blks_hit/nullif(blks_hit+blks_read,0),1) as cache_pct from pg_stat_database where datname=current_database()"
```

**Ce qui restait au-dessus du banc** : `validate` 13 ms et
`samples:forget` 33 ms. Mesuré chez l'utilisateur sans rien écrire
(objet en mémoire ; `SELECT`/`DELETE` d'UUID inexistants dans une
transaction annulée, comptage des relevés identique avant / après) :
valider le même corps 0,29 ms ; chercher les UUID 0,2 ms ; le `DELETE`
qui ne trouve rien 0,03 ms, mais son trigger des compteurs 5,7 ms.

**Changements** : (1) aucun `DELETE` quand aucun UUID envoyé n'est
stocké (relevés, entraînements) — plus de trigger pour rien ; (2) la
trace de chaque synchro contient `gc`, le temps passé par le processus
de l'API dans le ramasse-miettes de Python pendant la synchro (compté à
l'intérieur des autres étapes, pas en plus), pour voir si c'est lui qui
reste. Coût : deux appels d'horloge par passe du ramasse-miettes.

**Mesure** (banc HTTP de l'entrée 14, base factice, 3 démarrages × 6
synchros, deux passes ; `46271fe` contre le nouveau code) :
`samples:forget` médiane **4 → 1 ms**, `samples` 9 → 7 ms ; total en
régime normal 86 et 78 ms avant, 91 et 84 ms après (dans le bruit de
± 10 ms : sur le banc, le trigger ne coûtait que 1 à 3 ms) ; `gc` au
plus 4 ms. Empreintes des jours et des relevés identiques
(`e0fc6ac0…`, `039ae356…`), compteurs exacts.

**Résultat chez l'utilisateur** (`cc0726a`) : `gc` 1 à 2 ms — le
ramasse-miettes n'est pas en cause. Une synchro sans rien de neuf (134
sommes renvoyées, toutes inchangées) : **32 ms** au total (`validate`
1, `token` 7, `statistics` 12, `days` 0). Les étapes longues venaient
de la **première synchro de chaque processus** de l'API après un
redémarrage (4 processus, `API_WORKERS`) : connexion neuve (`token`
58 ms), premières requêtes préparées et premier passage dans le code
(`validate` 12, `samples:forget` 36 ms) — 212 ms. Ce coût ne revient
qu'après une mise à jour.

### 2026-10-01 (15) — supprimer un relevé ne relit plus l'historique des autres sources

**Constat** chez l'utilisateur, après l'entrée 14 (`045d400`) :
`deleted` 59–80 ms pour **un** UUID supprimé dans Santé, et
`samples:forget` 79–155 ms pour 6 à 15 relevés. Une suppression par UUID
devrait prendre une milliseconde.

**Cause** : le trigger qui tient `sample_counts` exact relit la
première ou la dernière date d'un groupe (compte, métrique, source)
quand une suppression la retire (entrée 12, migration `0029`). Le seul
index par date, `(user_id, metric_id, start_at)`, n'a pas la source :
la date du groupe `healthkit` ne venait qu'après tous les relevés de
l'export natif (`apple`) de la même métrique. Reproduit sur la base
factice (372 315 relevés de fréquence cardiaque `apple`, 576 de l'app),
le `DELETE` seul, dans une transaction annulée :

| Relevé de l'app supprimé | Sans l'index | Avec |
|---|---:|---:|
| le plus ancien | 10 738 ms | 2,2 ms |
| le plus récent | 666 ms | 5,7 ms |
| un du milieu | 1,8 ms | 1,7 ms |

**Changement** : index `ix_samples_group_start` `(user_id, metric_id,
source, start_at)` (migration `0031`) — le minimum et le maximum d'un
groupe en une descente d'index. Aucun code changé.

**Mesure par la synchro** (`healthkit_sync.sync`, processus chaud, deux
passes, transaction annulée) : une synchro qui supprime le plus ancien
relevé de fréquence cardiaque de l'app, `deleted` **121–140 → 8–9 ms** ;
le plus récent 11–12 → 7 ms ; un du milieu 7 → 6 ms. Banc HTTP de
l'entrée 14 avec, à chaque synchro, un UUID supprimé et un relevé
renvoyé : `deleted` 6–12 ms dans les deux cas (le relevé retiré y est le
plus récent, peu de relevés d'autres sources après lui), empreintes
identiques avec et sans l'index, compteurs exacts.

**Coût** : construit une fois au démarrage de l'API (9,7 s pour 2,4
millions de relevés, ≈ 2–3 s pour 600 000 ; les écritures attendent
pendant ce temps). Écriture : import de 315 000 relevés factices
(`imp_bench`, schéma neuf) 26,6 et 24,7 s avant, 24,9, 25,2 et 25,3 s
après — pas d'écart mesurable ; compteurs exacts.

**Tests (SQLite)** : avec ce nouvel index, SQLite choisissait selon la
requête l'un ou l'autre index, donc un autre ordre de lecture — et, à
égalité de relevés entre deux canaux, un autre canal pour le jour
(réconciliation entière contre découpée). La lecture « dans l'ordre de
la table » de `daily_rollup` y est maintenant explicite (`ORDER BY
rowid`), comme PostgreSQL lit déjà sans index (balayage ou bitmap,
ordre physique).

### 2026-10-01 (14) — une synchro ne réécrit plus les sommes inchangées

**Constat** (relevé des temps, entrée 13, chez l'utilisateur) : une
synchro de 10 relevés et 118 sommes, `total` 605 ms, dont `samples`
243 ms (premier appel après un redémarrage), `statistics` 171 ms et
`days` 112 ms. L'app renvoie à chaque synchro **toutes les heures du
jour** ; seule l'heure en cours a changé. Chaque somme était pourtant
effacée, réécrite, et le jour de chaque type recalculé — par type :
6 `DELETE`, 6 `COPY` (33,5 ms à eux seuls), 6 recalculs, et une
vingtaine de recherches de métriques.

**Changement** (`services/healthkit_stats.py`) : une somme déjà stockée
exactement comme envoyée (type, intervalle, valeur, unité) reste ; les
autres sont effacées puis écrites **en une instruction chacune pour
tous les types**, lues en une instruction (`UNION ALL`, une branche par
type sur l'index partiel des sommes : vérifié par `EXPLAIN` sur 78 828
sommes factices, chaque branche lit l'index par type et fin — un `OR`
pouvait ne lire l'index que par compte) ; seuls les jours modifiés sont
recalculés. Les métriques d'une synchro sont cherchées une fois, en une
requête ; sans sommeil ni entraînement, leurs métriques ne sont plus
cherchées. Même résultat que tout remplacer : les lignes gardées sont
celles qu'on aurait réécrites à l'identique.

**Méthode** : banc HTTP (`uvicorn` réel, un processus comme chacun du
hub), base factice de 2,4 millions de relevés, 29 jours de sommes
horaires déjà envoyés ; puis 3 démarrages × 6 synchros comme l'app :
10 relevés (fréquence cardiaque, repos, VFC, bruit) et les heures du
jour de 6 types (90 à 126 sommes), l'heure en cours qui grandit et une
nouvelle heure toutes les deux synchros. L'ancien code (`3c12288`) et
le nouveau, chacun depuis son propre dossier, deux passes.

| | Synchro habituelle (médiane) | 1ʳᵉ après un démarrage (médiane) |
|---|---:|---:|
| Avant (`3c12288`) | 148 ms, 143 ms | 225 ms, 215 ms |
| Après | **78 ms, 82 ms** (version finale : 74 ms) | **170 ms, 160 ms** (141 ms) |

Détail après, synchro habituelle : `statistics` 9–12 ms (50–84
avant ; dont `statistics:read` 2–4, `:delete` 3–4, `:write` 2),
`samples` 7–11 ms, `days` 41–54 ms (≈ 4 ms par métrique réellement
modifiée — le reste à gagner, dans le code partagé avec la
réconciliation).

**Mêmes réponses** : après les 18 synchros, empreinte md5 des valeurs
quotidiennes `healthkit` et des relevés (type, identifiant, début, fin,
valeur, unité) identique avant / après
(`e0fc6ac0…`, `039ae356…`), compteurs `sample_counts` exacts (0
écart). Tests : une somme renvoyée à l'identique garde sa ligne et ne
recalcule aucun jour ; l'heure modifiée seule est réécrite ; « Dernière
synchro » avance quand même ; une ligne refusée ne crée pas de
métrique ; « jamais compté deux fois » (par heure puis par jour)
inchangé — SQLite et PostgreSQL.

### 2026-10-01 (13) — où passe le temps d'une synchro de l'app iPhone

Pas une optimisation : un **relevé des temps**, pour savoir quoi
optimiser — aujourd'hui ou dans six mois. Chaque `POST /sync/healthkit`
chronomètre ses étapes et les écrit :

- dans le journal de l'API, une ligne JSON `healthkit_synced`, avec le
  **commit** du code qui l'a produite (`commit`) ;
- dans le journal d'audit du compte (champs `ms` et `commit`, gardés
  tant que la base l'est).

```bash
./version.sh && docker compose logs api --no-log-prefix | grep -E "healthkit_synced|sync/healthkit" | tail -6
./version.sh && docker compose exec db psql -U phoenix phoenix -c "select created_at, payload->>'commit' as commit, payload->'ms' from audit_log where action='sync' and entity='healthkit' order by created_at desc limit 10"
```

`./version.sh` affiche d'abord le code qui tourne (commit du dépôt,
de l'API et du worker, migration de la base, dernière mise à jour) : on
sait de quel code viennent les lignes qui suivent.

Les étapes, en millisecondes, dans l'ordre où elles tournent (l'ordre
de la ligne du journal ; dans l'audit, PostgreSQL range les clés à sa
façon) :

| Clé | Ce qui est mesuré |
|-----|-------------------|
| `receive` | Le corps de la requête reçu (de nginx), jusqu'à son dernier octet. |
| `json` | Sa lecture en JSON (FastAPI, avant toute vérification). |
| `token` | Le jeton vérifié (et la connexion à la base ouverte pour lui). |
| `validate` | Le JSON vérifié champ par champ (`HealthKitSync`). |
| `zone` | Le fuseau du compte. |
| `deleted` | Les relevés et entraînements supprimés dans Santé. |
| `samples` | Les relevés : lecture, remplacement par UUID, écriture… |
| `samples:forget`, `samples:write` | … dont les UUID renvoyés ôtés, et l'écriture. |
| `statistics` | Les sommes horaires… |
| `statistics:read`, `:delete`, `:write` | … dont la lecture de celles déjà stockées, l'effacement de celles qui changent, l'écriture des nouvelles. |
| `workouts` | Les entraînements. |
| `sleep` | Les nuits refaites depuis les phases. |
| `days` | Les valeurs quotidiennes recalculées, toutes métriques… |
| `days:<métrique>` | … et chacune (par ex. `days:heart.rate`) : la plus lente saute aux yeux. |
| `workout_days` | Les jours des entraînements. |
| `commit` | L'écriture en base (journal seulement : l'audit est écrit avant). |
| `gc` | Le ramasse-miettes de Python pendant la synchro (à l'intérieur des étapes ci-dessus, pas en plus). |
| `total` | De l'arrivée de la requête à la fin (dans l'audit : avant le `commit`). |

Le `total` part du même instant que la ligne d'accès de la requête
(`"POST /api/v1/sync/healthkit …" … ms`) : **durée de la ligne d'accès −
`total`** = l'écriture de la réponse, quelques ms. L'envoi depuis
l'iPhone jusqu'à nginx n'y est pas : nginx reçoit tout le corps avant de
le passer à l'API.

**Première mesure chez l'utilisateur** (avant `receive`…`validate`) :
6 relevés et 117 sommes horaires, 13 jours recalculés : `total` 277 ms
(ligne d'accès 296 ms), dont `statistics` 143 ms, `samples` 62 ms,
`days` 61 ms (8 métriques, 5 à 12 ms chacune). À creuser ensuite : les
sommes et les relevés, longs pour si peu de lignes.

Coût du relevé : 1,05 µs par étape mesurée (`timeit`, 200 000 fois),
une vingtaine d'étapes par synchro, soit moins de 0,05 ms. Aucune
réponse ne change (mêmes tests). Aucune valeur, date de relevé ou UUID
n'est écrit : des noms d'étape, des clés de métrique, des durées et le
commit.

### 2026-10-01 (12) — les petites synchros de l'app iPhone

Chez l'utilisateur, des synchros de **quelques relevés** (0 à 177
relevés et 111 sommes horaires) prenaient 1,2 à 3,5 s
(`docker compose logs api | grep sync/healthkit`, et leur contenu dans
`audit_log`). Deux causes, toutes deux par type de somme et par synchro :

1. **Le compteur de relevés** (entrée (3)) : la synchro remplace les
   sommes des dernières heures, et l'effacement retire la dernière date
   du canal `healthkit`. Le déclencheur relisait alors **les deux**
   dates ; la première, par un index qui ne connaît pas la source,
   n'arrivait qu'après tous les relevés plus anciens de l'export natif
   (925 628 lus pour en trouver un) : 160–180 ms à chaud, 12,6 s à
   froid. Il ne relit maintenant que la date effacée (`coalesce`) :
   **5,9–14,9 ms**, mêmes compteurs (migration `0029`).
2. **La recherche des sommes à remplacer** (`start < fin AND end >
   début`, présente depuis la création de la synchro) : sans index sur
   la fin, PostgreSQL lisait la métrique depuis 2021 jusqu'à la fin de
   la période (≈ 70 ms pour trouver, autant pour effacer). Un index
   **partiel** ne contient que les sommes de l'app, par leur fin
   (176 kB ici, 0,3 s à créer) : **12 ms → 0,06 ms**. Le motif
   `external_id LIKE 'stat:%'` est écrit tel quel dans la requête, sans
   paramètre, pour que PostgreSQL puisse toujours s'en servir (migration
   `0030`).

**Banc** : base de mesure (export natif), 29 jours de sommes horaires
`healthkit` pour 4 types déjà là, puis 6 synchros comme celles de
l'utilisateur (111 sommes remplaçant les dernières heures + 177
fréquences cardiaques), version poussée + base en `0028` contre nouvelle
version + base en `0030`, à tour de rôle, deux fois :

| | avant | après |
|---|---:|---:|
| une petite synchro | 640–1 030 ms | **92–174 ms** |

Jours écrits identiques (même empreinte), compteurs exacts (0 écart).
Le premier envoi complet (entrée (10)) ne bouge pas : 10,0 / 9,9 s
avant, 10,1 / 9,8 s après. Migrations jouées dans les deux sens sur
PostgreSQL et sur SQLite.

### 2026-09-30 (11) — écrire les relevés en un bloc (`COPY`)

SQLAlchemy confie une liste de lignes à asyncpg **une ligne à la fois**
(`executemany`, sans `RETURNING`). Le déclencheur qui tient
`sample_counts` exact, prévu pour tourner une fois par requête, tournait
donc une fois par ligne, et mettait à jour à chaque fois la même ligne
de compteur dans la même transaction : de plus en plus lent à mesure
que l'import avance. Ce déclencheur date de l'entrée (3) ; la mesure
faite alors (« ≈ 1 % ») insérait 5 000 lignes par requête SQL, pas
comme l'application : **la régression m'avait échappé**.

Les relevés sont maintenant écrits par `COPY` (PostgreSQL), en un bloc,
dans la même transaction, avec les mêmes contrôles (clés, identifiants
HealthKit uniques) et les valeurs par défaut des colonnes remplies comme
SQLAlchemy le faisait : synchro iPhone (relevés, sommes), Health Auto
Export, import Apple. Le sommeil, qui écrit une ligne à la fois, garde
l'insertion d'avant. SQLite (les tests) aussi.

**Mesures** :

| | ligne par ligne | `COPY` |
|---|---:|---:|
| 5 000 relevés, déclencheur compris | 0,59–0,66 s | **0,19–0,22 s** |
| Premier envoi de l'app (20 requêtes, entrée (10)) | 24,0–27,6 s | **11,6–12,3 s** |
| Import d'un export factice de 315 000 relevés | 198–218 s | **21–23 s** |

Pour l'import, la version d'avant le déclencheur mettait 25,7–25,9 s :
`COPY` fait mieux qu'avant la régression. (Méthode : export factice de
fréquence cardiaque toutes les 5 min et de pas toutes les 10 min sur
deux ans, importé dans une base PostgreSQL neuve, deux fois par version,
à tour de rôle.)

**Mêmes résultats** :
- import : relevés écrits identiques (même empreinte dans les 4
  passages), jours identiques (hors `recorded_at`, qui vaut l'heure de
  l'import) ;
- premier envoi de l'app : compteurs exacts (0 écart avec un comptage
  complet), jours identiques à la version précédente dans 9 passages sur
  11.

Les 2 autres diffèrent sur **un** jour, au 16ᵉ chiffre (78.22499999999978
contre 78.2249999999998) : le banc efface puis réinsère les mêmes relevés,
et PostgreSQL les range à des endroits différents de la table selon la
place libérée. Lus « dans l'ordre de la table », les relevés de ce jour
s'additionnent alors dans un autre ordre. L'ancienne version varie de
même d'un passage à l'autre (entrée (10)). À table identique, le
résultat est identique au bit près ; seule une somme exacte, qui ne
dépend plus de l'ordre, l'éviterait dans tous les cas.

### 2026-09-30 (10) — le premier envoi complet de l'app iPhone

L'app iPhone de l'utilisateur envoie tout l'historique la première
fois, puis des deltas. Une requête `POST /sync/healthkit` porte au plus
5 000 relevés et 5 000 sommes : deux millions de relevés, c'est au moins
400 requêtes. Chaque requête recalculait chaque métrique touchée **de son
premier jour reçu jusqu'à aujourd'hui** : une requête de 2023 relisait
2023–2026, export natif compris, et cela à chaque requête. Deux
changements, sans toucher au calcul d'un jour :
- **seuls les jours reçus** sont recalculés, du premier au dernier (les
  jours suivants gardent leurs relevés, donc leurs valeurs), lus dans
  l'ordre de la table comme par la réconciliation ;
- **les jours devenus vides** (plus aucun relevé de ce canal) sont
  trouvés par ce recalcul, qui vient de lire tous leurs relevés, et
  effacés en une requête, au lieu d'une requête par jour (225 par
  requête d'envoi ici).

**Banc** : sur la base de mesure (export natif déjà là), 20 requêtes
comme les enverrait l'app, les plus anciennes d'abord : chacune porte
5 000 fréquences cardiaques (une toutes les 5 min) et 5 000 sommes
horaires d'énergie au repos, à partir du 1ᵉʳ janvier 2023. Base remise à
l'identique avant chaque passage ; ancienne et nouvelle version à tour
de rôle, deux fois.

| | avant | après |
|---|---:|---:|
| 20 requêtes | 43,0–45,1 s | **24,4–27,2 s** |
| requête la plus longue | 3,7–4,4 s | **2,0–2,1 s** |
| jours recalculés | 29 300 | 1 713 |

**Mêmes résultats** : les deux passages de la nouvelle version donnent
la même empreinte de tous les jours, identique au premier passage de
l'ancienne. L'ancienne, elle, varie d'un passage à l'autre sur un jour
(énergie au repos du 7 mai 2025 : 1221.4 ou 1221.4000000000003) : elle
relisait tous les jours jusqu'à aujourd'hui dans l'ordre choisi par
PostgreSQL, qui change quand les statistiques de la table bougent. Un
test vérifie qu'un jour vidé perd bien sa valeur (il échoue sans
l'effacement).

**Ce qui reste** : l'écriture des lignes elles-mêmes (≈ 120 µs par
relevé, dont la moitié pour le compteur de relevés tenu par la base,
appelé à chaque ligne car SQLAlchemy les envoie une par une).

### 2026-09-30 (9) — plusieurs comptes réconciliés en même temps

Le `worker` exécute jusqu'à 10 tâches à la fois (`WORKER_MAX_JOBS`).
Dix comptes qui importent en même temps auraient lancé chacun
`RECONCILE_PARALLEL` processus : 40 processus et 40 connexions en plus,
près des 100 que PostgreSQL accepte (l'API et le worker en tiennent
déjà 50). Une seule réconciliation à la fois a maintenant ses processus
dans un worker ; les autres attendent leur tour sans garder de
transaction ouverte. Le calcul étant limité par le processeur, le temps
total pour tous les comptes ne change pas : chacun a tous les cœurs à
son tour au lieu d'un quart en même temps. Un compte d'une seule
métrique (ou `RECONCILE_PARALLEL=1`) ne lance aucun processus et
n'attend pas. Un test réconcilie deux comptes à la fois : jamais deux
groupes de processus en même temps, les jours des deux justes.

### 2026-09-30 (8) — couper une grosse métrique en périodes

Une réconciliation ne peut pas aller plus vite que sa plus grosse
métrique, qu'un seul processus calculait de bout en bout (chez
l'utilisateur : l'énergie au repos, 5,0–5,3 s sur ≈ 7 s). Une métrique
qui a au moins `RECONCILE_SPLIT_MIN_SAMPLES` relevés (100 000) et plus
que la part d'un processus (1/`RECONCILE_PARALLEL` des relevés du
compte) est maintenant coupée en périodes de jours d'environ une part
chacune, calculées en même temps par des processus différents. Les
coupures tombent au jour du relevé placé à 1/2 (1/3, 2/3…) de la
métrique, trouvé par l'index en ≈ 50 ms, pendant que les processus
démarrent.

Pour que chaque jour reste calculé exactement comme avant :
- la coupure tombe toujours à minuit (heure locale), jamais au milieu
  d'un jour ;
- chaque morceau lit un jour de plus de chaque côté, puis ne garde que
  ses propres jours : aucun changement d'heure ne peut déplacer un
  relevé dans le mauvais morceau (testé à la nuit du 29 mars) ;
- toute la réconciliation lit les relevés **dans l'ordre de la table**
  (jamais dans celui de l'index), métrique entière ou morceau, 1 ou N
  processus : un jour reçoit ses relevés dans le même ordre, donc la
  même somme au dernier chiffre et le même canal choisi. Les synchros
  gardent le choix de PostgreSQL.

**Trouvé en chemin, déjà présent avant** : quand les deux canaux
HealthKit (export natif et Health Auto Export) ont exactement autant de
relevés un jour donné, la règle garde celui qui arrive en premier à la
lecture. Le test du découpage sur PostgreSQL l'a montré : même valeur
(71,05), source `apple` à 13:00 lue par l'index, `auto-export` à 20:00
lue dans l'ordre de la table. Une synchro (lue par l'index) et une
réconciliation peuvent donc déjà choisir des canaux différents pour un
tel jour. La réconciliation lit maintenant toujours dans le même ordre ;
une règle d'égalité fixe (par exemple l'export natif d'abord) rendrait
le choix identique partout, mais changerait la valeur retenue de ces
jours-là : c'est une décision à prendre à part.

**Mesure** (machine de mesure, versions à tour de rôle, 3 fois,
médianes) : 1 processus 7,8 s → 7,8 s (lire dans l'ordre de la table ne
coûte rien) ; 4 processus 3,5 s → **3,2 s** (l'énergie active, 930 782
relevés, coupée en deux : « 1/2 » 1,4 s et « 2/2 » 1,3 s). Avec 2
processus rien n'est coupé ici (aucune métrique ne dépasse la moitié des
relevés). Sur 4 cœurs pleins le gain reste modeste ; chez l'utilisateur
(16 fils), il compte surtout avec `RECONCILE_PARALLEL=8`, où une métrique
est coupée dès qu'elle dépasse 1/8 des relevés.

**Chez l'utilisateur, après la mise à jour** (2 008 285 relevés,
60 métriques, les trois réglages lancés à la suite) :

| `RECONCILE_PARALLEL` | avant ce chantier | après |
|---|---:|---:|
| 1 | 17,7–18,7 s | **14,0 s** (lecture directe) |
| 4 | 6,8–7,1 s | **5,4 s** (énergie au repos coupée en 2) |
| 8 | — | **4,4 s** (repos en 3, énergie active en 2) |

L'empreinte (md5) de tous ses jours est **identique** avec 1, 4 et 8
processus : sur des données réelles, le calcul coupé et en parallèle
écrit exactement ce qu'écrit un seul processus. Depuis la première
version sur un seul cœur (16,6 s), la réconciliation est ≈ 4 fois plus
rapide avec 8 processus.

**Mêmes résultats** : les 44 016 jours ont le même md5 (`dddedef5…`)
avec 1, 3 et 4 processus, coupés ou non, après une lecture interrompue ;
les tests des synchros, de Health Auto Export, du travail et de
l'équivalence passent sur PostgreSQL. Un test coupe une métrique en deux
et compare aux jours calculés d'un bloc (il échoue si un morceau garde
ses jours de marge : deux processus écrivaient alors le même jour).

### 2026-09-30 (7) — lire les relevés sans la couche SQLAlchemy

Pour recalculer les jours d'une métrique, on lit tous ses relevés
(heure, valeur, unité, source). Mesuré sur la machine de mesure, c'est
cette **lecture** qui coûtait, pas le calcul : énergie au repos
(372 316 relevés) 0,9–1,1 s de lecture sur 1,4 s ; énergie active
(930 782 relevés) 2,0 s sur 2,8 s. Et dans cette lecture, la moitié
venait des objets « ligne » de SQLAlchemy :

| Lecture seule | SQLAlchemy (avant) | asyncpg directement |
|---|---:|---:|
| énergie au repos | 0,87–0,98 s | 0,52–0,60 s |
| énergie active | 1,80–1,90 s | 0,95–0,97 s |

Sur PostgreSQL, les relevés sont maintenant lus par le pilote asyncpg
lui-même, **avec la requête que SQLAlchemy compile** (même texte, mêmes
paramètres, donc même plan et même ordre des lignes), dans la même
transaction, par blocs de `ROLLUP_READ_BLOCK`. Le calcul qui suit n'a
pas changé. SQLite (les tests) garde la lecture d'avant. Tous les
recalculs en profitent : réconciliation, synchro iPhone, Health Auto
Export, saisies du travail.

**Mesure** (réconciliation complète, 2,4 M relevés, à chaud, ancienne
et nouvelle version à tour de rôle, médianes) :

| Processus | avant | après |
|---|---:|---:|
| 1 (et chaque synchro) | 10,4 s | **7,6 s** (−27 %, 5 fois sur 5) |
| 2 | 5,4 s | **3,9 s** (−28 %, 3 fois sur 3) |
| 4 | 3,9 s | **3,0 s** (−23 %, 5 fois sur 5) |

**Correction.** La première version de ce tableau donnait, avec 2 et 4
processus, 4,4 → 4,0 s et 3,5 → 3,5 s : la mesure était fausse. Les
processus d'une réconciliation sont lancés par `python -m`, qui lit
d'abord le code du dossier courant ; lancée depuis le dossier du
nouveau code, l'« ancienne » version avait donc des processus qui
exécutaient le nouveau. Chaque version est maintenant lancée depuis son
propre dossier (vérifié : l'ancienne parle un autre protocole et aurait
échoué avec les processus de la nouvelle). La mesure à 1 processus, où
tout se passe dans le processus principal, n'était pas touchée. Rien de
tel sur une vraie installation : le code et le dossier y sont les
mêmes.

**Mêmes résultats** : les 44 016 jours écrits ont le même md5
(`dddedef5…`) avec 1 et 4 processus, et après une lecture interrompue
de la table. Les tests des synchros, de Health Auto Export, du travail
et de l'équivalence des résultats passent sur PostgreSQL.

### 2026-09-30 (6) — la réconciliation sans temps mort

Chez l'utilisateur, une réconciliation de 9,1–9,3 s (4 processus) se
décomposait ainsi, mesurée étape par étape sur la version précédente
(les mêmes appels que `reconcile.run`, chronométrés un à un) :

| Étape | chez l'utilisateur | machine de mesure |
|---|---:|---:|
| catalogue + alias | 0,8–0,9 s | 0,1 s |
| recomptage des relevés | 1,2 s | 0,6 s |
| liste des métriques | 0,4 s | 0,2 s |
| jours (4 processus) | 6,7–6,8 s | 3,7–3,9 s |
| dont la plus longue métrique | 5,0–5,1 s | 3,1–3,3 s |

Deux temps morts, sans rapport avec le calcul :
- les 4 processus démarraient au début de la phase « jours » : leur
  chargement (1 à 2 s) s'ajoutait à la plus longue métrique ;
- le recomptage (une vérification des nombres de relevés) passait
  seul, avant.

Maintenant les processus démarrent **au début** de la réconciliation
et chargent leur code pendant le catalogue, la fusion des alias et la
liste (ils ne lisent rien avant qu'on leur donne une métrique), et le
recomptage se fait dans le processus principal **pendant** que les
autres calculent les jours. Son verrou sur les relevés dure le même
temps qu'avant (validé dès la fin du recomptage). Le calcul des jours
n'a pas changé d'une ligne.

**Mesure** (machine de mesure, 4 processus, à chaud, les deux versions
lancées à tour de rôle, 5 fois) : durée totale du programme,
lancement de Python compris, médiane **5,73 s → 5,30 s**, la nouvelle
plus rapide les 5 fois ; durée annoncée par la réconciliation
5,2 s → 4,6 s (médiane de 3). Sur 4 cœurs, les 4 processus, le
recomptage et PostgreSQL se partagent le processeur : le gain y est
plus faible que chez l'utilisateur (16 fils, plus de la moitié libres),
où il peut aller jusqu'à ≈ 2,9 s (1,7 s de démarrage et 1,2 s de
recomptage), à vérifier sur la ligne `reconciled` ou avec la commande
« 1 contre 4 processus » de la section (5).

**Chez l'utilisateur, après la mise à jour** (4 processus, deux
passages) : **6,8 s et 7,1 s**, contre 9,1–9,5 s avant (−2,4 s).
Depuis la première version à un seul cœur : 16,6 s → ≈ 7 s. Ce qui
reste : le démarrage des processus (≈ 1,7 s, plus long que les
premières étapes qu'il recouvre, 1,3 s) puis la plus longue métrique,
l'énergie au repos (5,0–5,3 s), qu'un seul processus calcule de bout
en bout.

**Mêmes résultats** : les 44 016 jours écrits ont le même md5 qu'avant
(`dddedef5…`) avec 1, 4 et 8 processus ; les nombres de relevés
recomptés sont exacts (0 écart avec un `GROUP BY` sur les 2 415 530
relevés). Un test vérifie que des nombres faussés sont bien corrigés
pendant le calcul des jours (et échoue si le recomptage est retiré).

### 2026-09-30 (5) — la réconciliation sur plusieurs cœurs

La réconciliation passait son temps en calcul Python, **sur un seul
cœur** : chaque relevé est lu, converti dans l'unité de la métrique,
puis ajouté à son jour (16,6 s chez l'utilisateur, dont 3,9 s pour la
seule énergie au repos). Les métriques ne partagent rien : chacune
n'écrit que ses propres jours. Elles sont donc maintenant recalculées
`RECONCILE_PARALLEL` à la fois (4 par défaut), chacune dans son propre
processus, avec sa propre connexion et **la même fonction**
(`daily_rollup.rebuild`, inchangée). Les métriques qui ont le plus de
relevés partent en premier, pour qu'une longue ne démarre pas seule à
la fin : chaque processus prend la suivante dès qu'il a fini. Chaque
processus est un programme à part (`python -m app.cli.rollup_worker`),
qui n'hérite d'aucune connexion du worker et ne dépend pas de la façon
dont la réconciliation a été lancée. Ils s'arrêtent avec elle.

(Première version : `multiprocessing` en `spawn`. Chaque processus
relisait alors le script principal, et une réconciliation lancée par un
script donné sur l'entrée de Python, `python - <<EOF`, échouait. Ce cas
est maintenant couvert par un test. Mêmes temps, mêmes jours, même md5
avec la nouvelle version.)

**Mesure** : machine de mesure (4 cœurs), 2,4 M relevés factices,
21 métriques, à chaud. Chaque réglage est lancé à tour de rôle avec
l'ancien code (arbre git du commit précédent, importé par `PYTHONPATH`),
trois fois, puis on garde la médiane.

| `RECONCILE_PARALLEL` | 1ʳᵉ série | 2ᵉ série |
|---|---:|---:|
| ancien code | 10,8 s | 9,7 s |
| `1` (une métrique après l'autre) | 10,6 s | 9,7 s |
| `2` | — | 6,3 s |
| `3` | — | 4,9 s |
| `4` (défaut) | 5,4 s | 5,2 s |

Sur 4 cœurs, 3 et 4 processus se valent : PostgreSQL et le processus
principal ont aussi besoin d'un cœur, et la plus grosse métrique
(énergie active, 3 à 4 s) fixe un plancher. Sur une machine avec plus
de cœurs libres (16 fils chez l'utilisateur), 4 garde de la marge.

**Mémoire et connexions** : 4 processus prennent 331 Mo au total au
pic (environ 85 Mo chacun, relevé dans `/proc` toutes les 0,2 s) et une
connexion chacun ; il n'en reste aucun une fois la réconciliation
finie.

**Mêmes résultats** : la table `measurements` est vidée de ses jours
Apple, recalculée, puis exportée triée (`COPY … ORDER BY`) et comparée
par md5. Les 44 016 lignes sont **identiques octet pour octet** avec
1, 2 et 4 processus, et aussi quand une lecture de la table a été
interrompue juste avant (6 passages, même md5).

**Un écart qui existait déjà, corrigé** : pour une grosse métrique,
PostgreSQL lit toute la table, en commençant là où la lecture précédente
s'est arrêtée (`synchronize_seqscans`). Après une lecture interrompue
(un curseur fermé en route), l'**ancien code** donnait donc 4 ou
5 jours différents sur 44 016, au 13ᵉ chiffre (1243.550000000001
contre 1243.5500000000009 kcal) : une somme de nombres à virgule dépend
de l'ordre. Avec plusieurs lectures en même temps, cela arrivait à
chaque fois. La lecture d'un recalcul part maintenant toujours du début
de la table (`SET LOCAL synchronize_seqscans = off`, pour cette
transaction seulement) : même ordre, mêmes sommes, sans coût mesurable
(la ligne `1` ci-dessus).

**À vérifier chez toi**, après la mise à jour (la réconciliation
automatique d'après mise à jour passe deux minutes après le démarrage
du worker) :

```bash
docker compose logs worker --since 30m | grep reconciled
```

`seconds` était de 16,6 s ; `slowest` donne maintenant le temps de
chaque métrique dans son processus.

**Chez l'utilisateur** (16 fils, machine partagée avec d'autres
conteneurs, 4 Go de mémoire disponible sur 62). La réconciliation
automatique juste après la mise à jour a pris 13,8 s (16,6 s avant),
chaque métrique environ deux fois plus longue que seule : elle tournait
pendant le redémarrage des conteneurs. Mesurée ensuite au calme avec la
commande ci-dessous, deux fois chaque réglage :

| | 1 processus | 4 processus |
|---|---:|---:|
| durée | 17,7 s et 18,7 s | **9,5 s et 9,5 s** |
| processeur libre | 64–67 % | 56–59 % |
| attente disque | 4–6 % | 3–7 % |
| temps volé | 0 % | 0 % |

Ni le processeur, ni le disque, ni l'hyperviseur ne saturent. Le
plancher est la plus longue métrique (énergie au repos, 5,3 s avec 4
processus, 4,6–4,9 s seule), qu'un seul processus calcule ; le reste
est fixe : recomptage des relevés, liste des métriques, démarrage des
processus. Sur la machine de mesure, à chaud : recomptage 0,6 s,
catalogue et alias 0,1 s, liste 0,2 s, jours 3,7–3,9 s dont 3,1–3,3 s
pour la plus longue métrique.

#### Mesurer chez soi : 1 contre 4 processus

Depuis le dossier du hub, avec l'identifiant du compte (le `user_id` de
la ligne `reconciled`). La réconciliation écrit les mêmes valeurs que
le bouton « Réconcilier » : rien ne change dans les données.

```bash
U=identifiant-du-compte
S='
import asyncio, sys
from app.core.db import SessionFactory
from app.services import reconcile
async def main():
    async with SessionFactory() as session:
        r = await reconcile.run(session, sys.argv[1])
    print("RÉSULTAT", r["seconds"], "s |", ", ".join(r["slowest"][:3]))
asyncio.run(main())
'
echo "cœurs $(nproc), charge $(cut -d' ' -f1-3 /proc/loadavg)"; free -m | sed -n 2p
for n in 1 4 1 4; do
  vmstat 1 > /tmp/vm.txt & VM=$!
  docker compose exec -T -e RECONCILE_PARALLEL=$n worker python -c "$S" "$U" 2>&1 | grep RÉSULTAT
  kill $VM; wait $VM 2>/dev/null
  awk -v n=$n 'NR==2{for(i=1;i<=NF;i++)c[$i]=i} NR>3{k++; us+=$c["us"]+$c["sy"]; id+=$c["id"]; wa+=$c["wa"]; st+=$c["st"]; bi+=$c["bi"]} END{printf "  -> %s processus : CPU occupé %d %%, libre %d %%, attente disque %d %%, volé %d %%, lu sur disque %d Mo\n", n, us/k, id/k, wa/k, st/k, bi/1024}' /tmp/vm.txt
done
```

Lecture : « libre » proche de 0 avec 4 processus → le processeur est
déjà pris (moins de processus n'y changera rien, plus non plus) ;
« attente disque » ou « lu sur disque » élevés → la table est relue sur
le disque faute de mémoire ; « volé » élevé → l'hyperviseur donne ces
cœurs à d'autres machines. Sur la machine de mesure : 1 processus
10,7 s, CPU occupé 28 %, libre 70 % ; 4 processus 5,5 s, occupé 71 %,
libre 28 %, rien lu sur le disque.

### 2026-09-30 (4) — la mémoire de PostgreSQL, réglable

Les réglages mémoire de PostgreSQL passent dans `.env` (`DB_SHARED_BUFFERS`,
`DB_EFFECTIVE_CACHE_SIZE`, `DB_WORK_MEM`, `DB_MAINTENANCE_WORK_MEM`,
`DB_SHM_SIZE`). Par défaut : les valeurs de PostgreSQL, rien ne change.

**Mesure** : machine de mesure, mêmes données (2,4 M relevés), chaque
réglage à chaud, puis juste après avoir vidé le cache du système
(`echo 3 > /proc/sys/vm/drop_caches`, ce qui arrive quand la mémoire
manque).

| | 128 Mo (défaut) | 2 Go, cache prévu 8 Go, work_mem 32 Mo, maintenance 512 Mo |
|---|---:|---:|
| `count(*)`, à chaud | 67 ms | 66 ms |
| Regroupement par métrique et source, à chaud | 203–217 ms | 236–271 ms |
| Le même, cache du système vidé | 532 ms | 564 ms |
| Réconciliation complète, à chaud | 10,8 s | 10,0 s |
| La même, cache du système vidé | 11,8 s | 11,3 s |

Sur cette machine (14 Go libres), **pas de gain net** :
- les lectures d'une table entière passent par un petit tampon à part,
  pas par `shared_buffers` ;
- le cache du système garde déjà tout ;
- la réconciliation passe son temps en calcul Python (un cœur), pas à
  lire la base.

Le réglage peut aider sur une machine dont le cache du système est à
l'étroit (4 Go disponibles sur 62 chez l'utilisateur) : à vérifier sur
place avec la ligne `reconciled` du worker (`seconds` : 17,0 s avant).

### 2026-09-30 (3) — inventaire, liste complète, tableaux de bord, réconciliation

Rien de retiré : mêmes données, même précision, chaque réponse comparée
à celle de l'ancien code.

**Méthode** : mêmes données factices (2 415 530 relevés, 44 016 valeurs
quotidiennes). L'ancien code (commit `c4a5a9d`) et le nouveau tournent
chacun dans un vrai serveur uvicorn, sur la même base, appelés **en
HTTP en alternance** (15 appels, médiane). Les **71 routes GET** du site
comparées : réponses identiques octet pour octet, sauf `/measurements`
(mêmes valeurs ; l'ordre entre deux valeurs du même jour et de la même
heure, 17 803 sur 44 016, était laissé au hasard de PostgreSQL : il est
désormais fixé par l'identifiant). Aucune route plus lente au-delà du
bruit de mesure (± 5 ms).

| Route (page) | Avant | Après |
|---|---:|---:|
| `/data/inventory` (Données → inventaire) | 364 ms | 23 ms |
| `/measurements` sans filtre (appel MCP sans métrique ni date, 12,9 Mo) | 2 130 ms | 404 ms |
| `/measurements?start=…` (depuis le 1er janvier, 6 566 valeurs) | 244 ms | 63 ms |
| `/measurements?metric_key=body.weight` | 32 ms | 17 ms |
| `/dashboard/nutrition` (tout l'historique, 14 600 points) | 213 ms | 78 ms |
| `/dashboard/activity` fenêtre 7 j / 365 j | 164 / 192 ms | 61 / 82 ms |
| `/dashboard/heart` | 42 ms | 24 ms |
| `/stock` (Journal → stock) | 154 ms | 80 ms |
| `/work/incomplete` (Travail → « À compléter ») | 291 ms | 181 ms |
| `/evidence` (Travail → preuves) | 205 ms | 123 ms |
| Réconciliation complète (worker, 2,4 M relevés) | 16,3 s | 11,9 s |

Causes et corrections :

1. **Inventaire** : il comptait les 2,4 millions de relevés à chaque
   affichage (286 ms sur 294). La table `sample_counts` garde, par
   métrique et par source, le nombre de relevés et leurs dates de début
   et de fin ; **la base elle-même la tient exacte** (déclencheurs sur
   `health_samples`, dans la même transaction que chaque écriture :
   import, synchro, fusion, suppression, suppression de compte). Lecture
   de la partie « relevés bruts » : 286 → 1,5 ms ; total vérifié égal au
   vrai comptage (2 415 530 = 2 415 530), aussi après des écritures
   annulées. **Ce que ça coûte à l'écriture** (100 000 relevés, lots de
   5 000 comme un import, 4 mesures de chaque, transaction annulée) :
   import 9,8 s avec la table contre 9,7 s sans (≈ 1 %, dans le bruit) ;
   suppression de 100 000 relevés 1,45 s contre 1,13 s (il faut relire
   la nouvelle première ou dernière date d'un groupe entamé).
   **Correction (entrée (11))** : cette mesure insérait 5 000 lignes par
   requête SQL ; l'application, elle, les envoyait une par une
   (`executemany` de SQLAlchemy), et le déclencheur tournait à chaque
   ligne. L'import réel de 315 000 relevés factices est ainsi passé de
   25,8 s à 198–218 s. Réparé par `COPY` : 21–23 s.
   Migration `0027` : 1,8 s sur 2,4 M relevés. « Réconcilier » la
   recalcule depuis les relevés, en contrôle.
2. **Ramasse-miettes de Python** : chaque passe complète reparcourait
   les centaines de milliers d'objets permanents de l'API (routes,
   schémas, tables) : 80 à 110 ms de plus sur une réponse qui crée
   beaucoup d'objets. Ils sont « gelés » une fois le processus démarré
   (`gc.freeze`, réglable : `GC_FREEZE`) ; tableau nutrition mesuré en
   processus : 184 ms (ramasse-miettes normal), 74 ms (gelé), 69 ms (sans
   ramasse-miettes du tout). Même chose dans le worker.
3. **Réponses revalidées par FastAPI** : une route qui renvoie un modèle
   le voyait reconverti en dictionnaire puis **revalidé en entier** avant
   d'être écrit (113 ms sur 264 pour un tableau de 14 600 points). Les
   tableaux de bord et les séries s'écrivent directement depuis leur
   modèle déjà validé (`core/responses.py`) ; leurs points sont validés
   en une passe au lieu d'un objet à la fois (14,7 → 2,3 ms pour 2 075
   points). Octets identiques.
4. **Moyenne glissante** : la fenêtre glisse le long des jours triés au
   lieu d'être recherchée pour chaque jour ; même calcul (`fsum` / nombre,
   ce que faisait `statistics.fmean`). 1 200 cas comparés (5 agrégations
   × 6 fenêtres × 40 séries aléatoires, jours en double compris) :
   identiques au bit près ; 4,7 → 2,3 ms par série.
5. **Liste des valeurs** (`/measurements`) : lues en colonnes (plus
   d'objets ORM) et écrites par le sérialiseur de pydantic directement
   depuis les types de la base, `value` lu par la même règle que le
   schéma (`first_set`) : même texte que le schéma, octet pour octet
   (test). La validation ligne par ligne coûtait 420 à 620 ms.
6. **En-têtes de sécurité** : l'intergiciel `BaseHTTPMiddleware`
   recopiait chaque réponse par morceaux ; réécrit en ASGI simple (les
   mêmes quatre en-têtes, ajoutés de la même façon : même test passé sur
   l'ancien et le nouveau).
7. **Réconciliation** : lecture des relevés sans la couche ORM, conversion
   d'unité préparée une fois par unité au lieu d'être refaite pour chacun
   des 2,4 M relevés (même règle, même calcul : testé au bit près sur
   chaque paire d'unités), comparaisons directes au lieu de `min()` /
   `max()`. Les 37 238 jours des 21 métriques calculés par l'ancien et le
   nouveau code : identiques (valeur à pleine précision, source, heure).
   Lecture et calcul 13,8 → 10,3 s. Les synchros (Health Auto Export,
   app iPhone), qui recalculent leurs jours de la même façon, en
   profitent aussi.

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

- **La réconciliation complète** : environ 5 s pour 2,4 millions de
  relevés et 21 métriques sur la machine de mesure avec 4 processus
  (10 s sur un seul cœur) ; 16,6 s chez l'utilisateur avant le passage
  en parallèle (2 008 285 relevés, 60 métriques). Elle tourne dans le
  `worker`, pas dans l'API : les pages restent libres pendant ce temps.
  Son journal donne sa durée et ses cinq métriques les plus longues
  (`docker compose logs worker | grep reconciled` : `seconds`,
  `slowest`). La plus grosse métrique fixe le plancher (3,9 s chez
  l'utilisateur pour l'énergie au repos) : un seul processus la
  calcule. Descendre plus bas demanderait de ranger les relevés par
  jour **dans PostgreSQL** : la règle du jour existerait alors en deux
  copies (SQL et Python), qui finiraient par diverger. **Écarté**
  ([idées](idees.md)).
- **`/measurements` sans aucun filtre** (≈ 0,4 s) : 44 000 valeurs,
  12,9 Mo. Le site filtre toujours ; seul un assistant MCP appelé sans
  métrique ni date le demande.
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
