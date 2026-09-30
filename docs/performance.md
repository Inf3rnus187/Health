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
