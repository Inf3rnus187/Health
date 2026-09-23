# Guide — utiliser le hub, page par page

## Le principe : une seule vérité

Chaque mesure a **une seule clé** (ex. `body.weight`, `bio.hba1c`,
`liver.cap`, `habit.cigarettes`), quelle que soit sa source : export Apple
complet, Health Auto Export, Raccourci, prise de sang PDF, document lu par
l'IA, saisie. Toutes les pages lisent les **mêmes** valeurs
(« vue d'ensemble » d'une métrique : dernier relevé, moyenne du jour,
moyennes 7 / 30 jours, sources).

- **Relevés bruts** : chaque mesure horodatée (Apple, Health Auto Export).
- **Valeurs journalières** : recalculées depuis le brut avec une règle
  unique — un seul canal Apple par jour (l'export natif et Health Auto
  Export portent les mêmes données : jamais additionnés), plus les autres
  sources ; une saisie explicite (pesée, labo) est conservée.
- Une valeur connue seulement par son jour (labo, FibroScan) est datée du
  jour de l'examen, sans heure inventée.
- Les 121 types de mesures et 72 types d'événements du SDK Apple Santé
  (iOS 26) ont un libellé français et un domaine ; les symptômes, heures
  debout, notifications cardiaques, pleine conscience… deviennent des
  nombres traçables.

## Accueil

Tuiles des mesures clés (dernière valeur, moyenne 7 j, évolution) — un clic
ouvre la mesure dans **Données** avec son graphique. Saisie rapide du poids.

Tuiles, dans l'ordre (une mesure sans aucune donnée n'apparaît pas) :
poids, pas, **km marchés / courus** (`activity.distance`, total du jour),
FC au repos, fréquence cardiaque, VFC, sommeil, SpO2, fréquence
respiratoire, énergie active, minutes d'exercice, cigarettes, cafés,
**pipi** (`elimination.urination` : nombre du jour et heure du dernier),
**heures travaillées** (`work.hours`), eau (litres = bouteilles × 1,5). Une tuile montre le dernier jour qui a une
valeur, avec sa date. La liste est `HEADLINE_KEYS` dans
`backend/app/services/summary.py`.

## Tableaux de bord

Un onglet par domaine (Mesures corporelles, Cœur, Biologie, Activité,
Sommeil, PPC, Habitudes…), courbes jour / semaine / mois / année, zoom à la
molette.

## Santé

Signes vitaux (tendances), séances, ECG (courbe, CSV), parcours GPS (carte,
GPX), observations du dossier CDA importé.

## Données

- **Tout ce qui est enregistré** : chaque métrique, ses relevés bruts et
  valeurs journalières par source avec leurs dates — c'est l'endroit pour
  vérifier que Apple, Health Auto Export et les labos concordent.
- **Réconcilier et recalculer les valeurs journalières** : fusionne les
  clés en double, aligne les données sur le catalogue Apple, recalcule
  chaque valeur journalière depuis le brut. **Aucune IA.** À lancer après
  une mise à jour du hub ou un gros import.
- **Une mesure en détail** : choisir une métrique → graphique + chiffres.
- **Données brutes** : relevés paginés, filtrables par métrique et dates.

## Journal

Ce qu'Apple Santé n'enregistre pas : **pipi** et **repas**.

- **Pipi** : « Pipi maintenant » (ou une autre heure du jour) ; la liste des
  heures du jour, supprimables. Chaque miction est horodatée ; la valeur
  du jour (`elimination.urination`) est le nombre de mictions — courbes,
  tableaux de bord, Suivi (diabète, apnée du sommeil) et rapports la
  voient comme toute autre mesure.
- **Ajouter un repas** : type (petit-déjeuner, déjeuner, collation, dîner),
  date et heure, **description** (quantités, cuisson, « sans huile ni
  beurre »…) et **photo** facultative (sur téléphone, l'appareil photo
  s'ouvre). La photo est nettoyée (EXIF et GPS retirés), redimensionnée et
  chiffrée si le chiffrement est activé.
- **Analyse IA du repas** (une à quelques minutes) : aliments et
  quantités, **nutriments** (énergie, protéines, glucides dont sucres,
  lipides dont saturés, fibres, sodium), **note 0–10**, verdict, points
  positifs et à surveiller **pour vos maladies déclarées** (stéatose,
  diabète…). Voir le [guide IA](ia-medicale.md#repas).
- Les nutriments d'un repas rejoignent les **mêmes mesures nutrition
  qu'Apple Santé** (`nutrition.energy`, protéines, glucides…) ; modifier,
  réanalyser ou supprimer le repas remplace ou retire exactement ses
  nutriments.
- **Repas** de la période (7 jours par défaut, ou dates exactes), groupés
  par jour avec le total du jour, 10 jours par page.

Depuis l'iPhone : voir [Raccourcis iPhone](#raccourcis-iphone--une-seule-règle).

## Raccourcis iPhone — une seule règle

**Un seul jeton pour tous les raccourcis** : Import › « Jetons d'accès
(API) » › cocher `write:measurements` (il écrit, il ne lit rien).

### Compter quelque chose : bouteille, café, cigarette, pipi…

Toujours **la même action, la même URL, le même champ** ; seule la
valeur de `metric` change d'un raccourci à l'autre.

- Action **« Obtenir le contenu de l'URL »**
- URL : `https://<hub>/api/v1/sync/tally?token=<jeton>`
- Méthode **POST**, Corps de la requête **JSON**
- Champ `metric` (Texte) = la clé du tableau ; champ `amount` (Nombre)
  facultatif : `1` par défaut, `-1` pour annuler un appui de trop.

| Raccourci | `metric` |
|-----------|----------|
| Bouteille d'eau 1,5 L | `water.bottles_1_5` |
| Café | `habit.coffee` |
| Cigarette | `habit.cigarettes` |
| Envie de fumer cassée | `habit.urges_broken` |
| Pipi | `elimination.urination` (noté à l'heure de l'appui) |
| Embauche | `work.start` (pointe l'arrivée maintenant) |
| Embauche à distance | `work.remote_start` (ouvre une session à distance, même après la journée sur place) |
| Débauche | `work.end` (clôt la session ouverte, sur place ou à distance) |

Chaque appui **ajoute** au total du jour et n'efface jamais rien ; la
réponse donne le total avant (`previous`) et après (`total`). Pour
l'embauche et la débauche, `total` est le nombre d'heures travaillées du
jour et `detail` une phrase à afficher en notification (« Débauche 17:31
— 8 h 49 aujourd'hui »).

**Pointer automatiquement avec le GPS** : Raccourcis › Automatisation ›
« Arrivée » (lieu : le travail) › action « Obtenir le contenu de l'URL »
ci-dessus avec `metric` = `work.start` ; une seconde automatisation
« Départ » avec `work.end`. Désactiver « Demander avant d'exécuter ». Un
deuxième déclenchement d'arrivée pendant qu'une session est ouverte est
ignoré.

### Noter un repas : description + photo

Le seul autre chemin, parce qu'un repas transporte une photo — même jeton.

- Action **« Obtenir le contenu de l'URL »**
- URL : `https://<hub>/api/v1/meals?token=<jeton>`
- Méthode **POST**, Corps de la requête **Formulaire**
- Champs : `description` (Texte, p. ex. le résultat de « Demander une
  entrée ») et `file` (Fichier, le résultat de « Prendre une photo ») —
  l'un des deux suffit. Facultatifs : `meal_type` (`breakfast`, `lunch`,
  `snack`, `dinner` ; sinon déduit de l'heure) et `eaten_at` (sinon
  maintenant).

L'analyse IA apparaît ensuite dans **Journal**.

> Un raccourci déjà réglé sur `POST /api/v1/journal/urination?token=…`
> (sans corps) continue de marcher : c'est la route du bouton « Pipi
> maintenant ». Pour un nouveau raccourci, suivre la règle ci-dessus.

## Travail

Les heures de travail comme donnée de santé : amplitude, heures
supplémentaires et semaines chargées se lisent à côté du sommeil, de la
VFC ou de la tension — jusqu'à un dossier complet pour faire valoir un
arrêt, un accident du travail ou une maladie professionnelle. La page a
trois onglets : **Pointage**, **Dossier travail et santé**, **Importer**.

**Périodes et pages, partout pareil.** Chaque liste ou calcul daté
(heures travaillées, sessions, synthèse du dossier, preuves et traces,
nuits, repas, rapports) a le même sélecteur : raccourcis **7 j**,
**30 j**, **3 mois**, **1 an**, **Tout** (depuis la première donnée), et
deux dates exactes **Du … au …** pour n'importe quelle période. Les
listes longues se lisent **page par page** : « Par page » (10 par
défaut, ou plus) et « Précédent / Suivant ». Les jours s'entendent à
l'heure locale : un taxi à 00:30 compte pour ce jour-là.

### Pointage

- **Pointer** : « Embauche maintenant » / « Débauche maintenant », le
  Raccourci iPhone (même règle que les compteurs, voir plus haut, avec le
  GPS), ou l'assistant MCP (« j'embauche », « je débauche »). Une
  **session** va de l'embauche à la débauche ; plusieurs sessions par jour
  (pause déjeuner) s'additionnent. Une session appartient au jour où elle
  commence ; **72 h au plus** (48 h sans partir, ça arrive) ; deux
  sessions ne se chevauchent pas.
- **Travail à distance** : « Embauche à distance » (bouton, Raccourci
  `work.remote_start`, ou l'assistant : « je bosse à distance »), ou une
  session ajoutée avec « À distance » coché (« de 21:00 à 23:30 ») —
  **même un jour déjà travaillé sur place** : c'est une session à part,
  marquée « à distance ». Elle compte dans les heures du jour, la
  débauche, l'amplitude et le repos de 11 h (c'est du temps de travail),
  et à part dans `work.remote_hours`. Une embauche à distance pendant
  qu'une session sur place est encore ouverte (débauche oubliée) ouvre
  sa propre session ; la session sur place devient une journée à
  compléter. Le tableau de bord montre « **Dont à distance** » (heures,
  jours, et combien **en plus d'une journée sur place**), le graphique
  empile la part à distance en violet ; exports (colonne « lieu », « dont
  distance »), rapport PDF et dossier travail ↔ santé (« dont 2,5 h à
  distance » dans le journal du jour) la reprennent.
- **Rien n'est perdu** : une débauche sans embauche en cours (retour de
  pause non pointé, GPS muet) est gardée comme session « embauche
  manquante » ; une embauche jamais close devient « débauche manquante »
  au bout de 16 h. Une deuxième embauche le même jour pendant qu'une
  session est ouverte est ignorée.
- **Journées à compléter** : toutes les sessions incomplètes (la plus
  récente d'abord), avec « **preuve présente** » ou « sans preuve » et
  un filtre (avec / sans preuve, embauche ou débauche manquante). Chaque
  journée est une fiche : ce qui est connu (« Embauche 08:40 · Débauche
  ? à compléter »), puis de quoi retrouver l'heure vous-même :
  - les **preuves et traces du jour**, en tableau (type, heure, détail,
    montant) ; pour une débauche manquante, aussi celles du **lendemain
    matin** (le taxi de 03:47) ; un séjour qui couvre le jour (hôtel,
    parking de plusieurs jours) propose aussi sa fin. **« Voir »** ouvre
    le reçu, la facture ou la capture **dans un nouvel onglet** (jamais
    en téléchargement), pour vérifier par exemple d'où partait le VTC
    avant de choisir ; « Télécharger » à côté l'enregistre ; « Détails »
    montre ce qui a été lu (lieu, montant, texte de la facture) ;
    « Prendre 23:52 » / « Prendre la fin » reprennent son heure ;
  - le **réveil** et les **premiers pas** du jour (embauche manquante),
    les **derniers pas** et le **coucher** (débauche manquante) ;
  - votre heure **habituelle ce jour de la semaine** (« habituel le
    mercredi 19:05 ») et tous jours confondus (médianes des sessions
    complètes).

  Un clic pré-remplit l'heure (placée le lendemain si elle tombe avant
  l'embauche : 01:30 après une embauche à 08:00) ; ajustez-la, notez
  **d'où vient l'heure**, puis « Compléter ». Le hub ne choisit jamais
  seul. La session est marquée « corrigée à la main » (le rapport dit
  quelles heures ont été saisies).
- **Une erreur se corrige** : sous les journées à compléter, « **Corrigées
  à la main** » liste toutes les sessions complétées ou modifiées après
  coup ; « Modifier » rouvre l'embauche, la débauche, le lieu (sur place /
  à distance) et la note, avec les preuves du jour (« Voir », « →
  embauche », « → débauche »). Vider une heure remet la journée à
  compléter. Même « Modifier » sur chaque ligne des Sessions.
- **Valeurs du jour**, comme toute mesure (courbes, Données, tableaux de
  bord, exports, rapports) : `work.hours` (heures des sessions
  complètes, à distance comprise), `work.remote_hours` (la part à
  distance), `work.start` (première embauche) et `work.end` (dernière
  débauche), ces deux-là en heures décimales (8,25 = 08:15 ; 25,5 = 01:30
  le lendemain). Une journée incomplète n'a pas d'heures : les totaux sont
  des **minimums**.
- **Heures travaillées** sur la période choisie (raccourcis ou dates
  exactes) :
  total, jours travaillés, moyenne par jour, embauche et débauche
  moyennes, **heures supplémentaires** (par semaine, au-delà du contrat —
  35 h par défaut, réglable — règle légale : heures faites), **jours de
  plus de 10 h** et **semaines de plus de 48 h** (maximums du Code du
  travail), plus longue journée ; graphique par semaine et tableau
  court / moyen / long terme.
- **Arrêts, congés, repos et jours fériés comptent** (Arrêts et
  absences, saisis ou importés ; fériés d'office) :
  - une tuile par type : jours calendaires et jours ouvrés dans la
    période, et « **Travaillé pendant une absence** » (les dates) ;
  - la **moyenne par semaine** ne prend que les **semaines complètes**
    (sans absence ni férié) : une semaine avec deux jours d'arrêt n'est
    pas une petite semaine de travail ;
  - l'**objectif de chaque semaine** est le contrat moins ses jours
    ouvrés d'absence (35 h, 21 h avec deux jours d'arrêt, 0 h en
    congés) ; « **Au-delà de l'objectif** » cumule ce qui le dépasse
    (trois jours de 11 h entre deux jours d'arrêt : 12 h) ;
  - graphique : barres **orange** les semaines d'arrêt, **grises** les
    semaines de congés, repos ou férié (rouge au-delà de 48 h prime),
    objectif réduit en **pointillés** ; une semaine entière d'absence
    apparaît, vide ;
  - tableau court / moyen / long terme : jours d'absence et moyenne **par
    semaine présente** (jours d'absence, fériés et jours d'avant le
    premier pointage ôtés) ;
  - l'export par jour liste aussi les jours d'absence (colonne
    « absence »), l'export par semaine l'objectif et les jours d'absence,
    le rapport PDF et le dossier travail ↔ santé les mêmes chiffres.
- **Exporter** la période par jour, semaine, mois ou session, en CSV,
  Excel ou JSON ; **Rapport PDF** des heures (aussi dans Rapports ›
  « Heures travaillées »).
- **Sessions** de la période (30 jours par défaut), page par page, avec
  un filtre (corrigées à la main, à distance, incomplètes) : vérifier,
  ajouter une session oubliée (l'embauche, la débauche ou les deux),
  **modifier** (heures, lieu, note, avec les preuves du jour),
  supprimer (après confirmation).
- « **Au travail depuis** » ne concerne qu'une embauche de moins de 16 h :
  une embauche ancienne jamais close est une journée à compléter et ne
  bloque plus le bouton « Embauche maintenant ».

### Dossier travail et santé

- **Synthèse** (1 an par défaut, ou toute période exacte) : sessions et journées incomplètes,
  nuits connues, repères du Code du travail, liens travail ↔ sommeil, et
  « **Générer le rapport PDF complet** » (aussi dans Rapports ›
  « work_health » via l'API ou l'assistant).
- **Arrêts et absences** : arrêt maladie, accident du travail, maladie
  professionnelle, congés, **repos** (RTT, récupération), autre — dates,
  **cause**, notes ; ou importées de votre outil RH (voir Importer).
  **Demi-journées** : « Du 07/05 à partir de l'après-midi » et / ou « au
  08/05 jusqu'à midi » ; une matinée seule : même jour, « jusqu'à midi ».
  Une demi-journée compte ½ partout (jours d'absence, objectif de la
  semaine : 31 h 30 au lieu de 35 h ; travailler l'autre moitié n'est pas
  « travailler pendant une absence »). **« Modifier »** rouvre une
  absence ; supprimer demande confirmation. Le rapport
  liste pour chacun le **travail pointé pendant l'arrêt** et les **preuves
  datées pendant l'arrêt** (appels, dont le dimanche).
- **Documents : une seule règle**, comme les documents du Dossier
  médical : « **Voir** » ouvre le fichier dans un nouvel onglet (PDF,
  image), « **Télécharger** » l'enregistre — pour chaque preuve et trace
  (liste, journées à compléter, correction d'une session) et pour les
  rapports PDF (page Rapports). Les exports de données (CSV, Excel,
  JSON) se téléchargent.
- **Preuves et traces**. Preuves : appel, SMS, mail, capture d'écran,
  note, document — date et heure, **nombre** (« 12 appels » sur une même
  capture), titre, description, fichier (30 Mo au plus, chiffré au repos
  si activé). **Traces** — ce que des tiers ont enregistré : transport
  (métro, Navigo, train), taxi / VTC, parking, **repas livré** (Uber
  Eats…), repas acheté, hôtel, note de frais — avec en plus l'heure de
  **fin** (sortie du parking, arrivée du taxi, départ de l'hôtel), le
  **lieu** et le **montant**. Un repas livré ou acheté peut être
  **ajouté au Journal** (case cochée par défaut) : le repas y est créé à
  l'heure de la commande, avec l'enseigne, ce qui a été commandé et son
  **prix**, puis lu par l'IA (nutriments, note sur 10). Chaque fichier
  garde son **empreinte SHA-256** calculée à la réception, imprimée dans
  le rapport : une copie se vérifie contre l'original
  (`sha256sum fichier`). Les images (PNG, JPEG) sont reproduites dans
  l'annexe du rapport ; les autres fichiers y sont listés.
  **Nommez vos fichiers avec la date et l'heure** : l'heure est souvent
  absente du PDF alors que c'est elle qui compte. Au choix du fichier,
  « Quand » se remplit tout seul depuis le nom — `2026-05-09 03h47.pdf`,
  `09-05-2026_03.47.png`, `2026.05.09 3h47.jpg`, `IMG_20260509-0347.jpg`
  (jour-mois-année ou année-mois-jour, séparés par `-`, `_`, `.` ou une
  espace ; heure `03h47`, `03:47`, `03.47`, `03-47`). La liste se
  filtre par période et par type (preuves, traces, ou un type précis),
  la plus récente d'abord, page par page.
- **Nuits** (30 jours par défaut ; « Tout » remonte à la première nuit
  connue), la plus récente d'abord, page par page ; « Montrer les nuits
  sans données » se décoche : pour chaque nuit (rattachée au jour du
  réveil, de 18 h la veille à 18 h), le sommeil, le nombre de **réveils**
  (phases d'éveil de la montre ; sans phases, les coupures de 5 min et
  plus), les **blocs** (sommeil « en plusieurs fois », coupé d'une heure
  ou plus), coucher et lever. Quand plusieurs appareils ont enregistré la
  même nuit, celui qui a vu le plus de sommeil est retenu (pas de double
  compte). Une nuit sans donnée (montre déchargée) se **saisit** :
  coucher, lever, réveils — marquée « saisie » dans le rapport.

Le **rapport PDF complet** (« Dossier travail et santé ») contient, dans
l'ordre :

1. **Méthode et sources** : sessions par origine (pointage, historique
   importé, saisie, complétée à la main), journées incomplètes non
   comptées, nuits connues par origine, jours travaillés sans donnée de
   sommeil.
2. **Travail** : heures (sessions complètes), jours de présence pointée,
   moyennes, embauche / débauche moyennes, heures au-delà du contrat,
   jours > 10 h, semaines > 48 h, plus longue journée.
3. **Repères du Code du travail**, avec les dates : repos quotidien de
   moins de 11 h, amplitude de plus de 13 h, sessions de 12 h et plus,
   moyenne de plus de 44 h sur 12 semaines, dimanches et jours fériés
   travaillés, heures de nuit (21 h - 6 h), plus longue suite de jours
   travaillés.
4. **Travail et sommeil** : corrélations (heures travaillées / sommeil
   de la nuit suivante, / réveils, heure de débauche / sommeil) avec r, le
   nombre de jours et une lecture en clair ; sommeil moyen, réveils et
   blocs après un jour non travaillé, < 8 h, 8-10 h, > 10 h (les journées
   incomplètes sont exclues) ; graphique heures par semaine et sommeil
   moyen.
5. **Par année, mois et semaine** : jours, heures, heures au-delà du
   contrat, nuits, sommeil, réveils, FC au repos, VFC, cigarettes et cafés
   par jour.
6. **Arrêts et absences** avec travail, preuves et traces pendant chacun.
7. **Traces et dépenses** : nombre et montant par type ; jours **sans
   pointage où une trace vous place quelque part ou montre votre
   activité** (présence attestée par un tiers, tickets traités) ; traces après 21 h un jour travaillé ; repas livrés ou
   achetés (nombre, montant, après 21 h, les jours longs — plus de 10 h ou
   débauche après 21 h —, note moyenne IA) ; lien heures travaillées /
   dépense repas du jour ; dépenses par mois et par type.
8. **Journal jour par jour** : embauche, débauche, heures, remarques
   (incomplète, absence, dimanche, férié), **traces du jour** (métro
   07:52, livraison 21:15 24,90 €…), sommeil de la nuit suivante,
   réveils, blocs.
9. **Annexe : preuves et traces**, avec empreintes et images.

Le document rassemble des faits enregistrés ; ce n'est ni un avis médical
ni un avis juridique. Une corrélation décrit un lien dans les données, pas
à elle seule une cause.

### Importer

**Historiques de Raccourcis** (un horodatage par ligne, un fichier par
type, comme les exports des Raccourcis iOS : `12 | 13/05/2025 07:42`) :
choisir **tous les fichiers ensemble** ; le type est deviné du nom
(Embauche, Débauche, Cigarettes, Café, Eau, Pipi, Envies) et modifiable.
« Lire » montre ce qui a été compris, « Importer » enregistre.

- **Embauches + débauches** sont appariées : même jour, ou débauche le
  lendemain matin avant midi (20 h au plus) ; une embauche répétée le même
  jour garde la première ; une débauche seule ou une embauche seule
  deviennent des sessions à compléter. Une session de plus de 20 h (48 h
  sans partir) se saisit à la main.
- **Cigarettes, cafés, eau, envies** : comptés par jour. Un jour sans
  valeur reçoit le compte ; un jour qui a déjà une valeur garde la plus
  grande des deux (jamais additionnées deux fois, jamais baissées).
- **Pipi** : une entrée horodatée par ligne ; une heure déjà enregistrée
  (± 1 min) n'est pas ajoutée deux fois.
- Réimporter les mêmes fichiers ne crée aucun doublon ; ajouter plus tard
  un fichier de débauches complète les embauches seules déjà importées
  (20 h au plus d'écart).

**Traces : exports des applications et reçus** — Uber, Uber Eats,
Navigo, parking, hôtel, notes de frais, relevé bancaire en CSV, Excel
(.xlsx) ou JSON, et **reçus / factures en PDF ou en photo**. Choisir les
fichiers, vérifier le **type** de chacun (« Deviner » par défaut ; sinon
deviné du nom : `trips_data` → taxi, `eats` → repas livré, `navigo` →
transport…), « Lire », puis « Importer ».

- **Reçus et factures** (PDF avec texte, PDF scanné ou photo lus par
  OCR) : la date, **l'heure** (tirée du nom du fichier quand il la porte,
  comme les reçus Uber `09-05-2026-03H47-….pdf`, sinon du texte), le
  **montant total payé**, qui a facturé (« Uber — TRANSPORTS TEST »), les
  lignes facturées et le numéro de facture. Le fichier est gardé comme
  preuve (SHA-256).
- **Un reçu et sa ligne de note de frais ne font qu'une trace** : même
  type, même jour, même montant, et heures égales ou l'une inconnue. Dans
  un sens comme dans l'autre, la trace est complétée — l'heure et le
  fichier du reçu, le motif de la note de frais — et comptée une fois
  (« rapprochées » dans l'aperçu).
- **Notes de frais** : une colonne qui nomme le type de chaque ligne
  (taxi, parking, dîner, déjeuner, hôtel, train…) l'emporte sur le type
  du fichier ; les colonnes sans titre ou non reconnues (motif, « Heures
  supp suite incident », plateforme…) sont gardées dans la description ;
  un texte « parking du 2/04/26 10h05 au 05/04/2026 23h32 » donne le
  **début et la fin** exacts. Un séjour de 6 h ou plus (parking, hôtel)
  compte comme **présence sur chaque jour** qu'il couvre.
- **Notes de frais Lucca en PDF** (l'archive `NDF-…pdf` à valeur
  probante, ou la note imprimée) : une trace par dépense — jour, nature
  (taxi, hôtel, autres frais…), fournisseur, montant TTC, montant payé
  en devise, et le **commentaire** (« Heures tardives suite incident »).
  Une note de frais ne donne que le jour : l'heure vient du reçu ou de
  l'export Uber du même trajet, rapproché (même jour, même montant). Le
  PDF est gardé **intact** comme document (SHA-256) : le cachet
  électronique d'une archive reste vérifiable sur l'original. Importer
  l'archive puis la note imprimée ne crée aucun doublon (la seconde
  n'ajoute que ce qui manquait, par exemple « payé 49,00 $ »).
- **Tickets (NinjaOne…)** : l'export CSV des tickets et de leurs
  commentaires. Seuls **vos** commentaires comptent : l'auteur le plus
  actif est proposé, choisissez votre nom dans la liste de l'aperçu
  (« Alex Martin (120 actions) »). Une trace **Activité pro** par jour, de la
  première à la dernière action (l'heure de début saisie dans le ticket
  compte), chaque action listée — heure, n° et objet du ticket, « privé »
  — sans le texte des commentaires ni les coordonnées des demandeurs.
  Elle sert partout : jours travaillés sans pointage, **traces tardives**
  d'après la dernière action (« 23:10 tickets »), indices des Journées à
  compléter (début et fin d'activité). Un export plus récent complète
  les jours déjà importés.

**Absences : export de l'outil RH** (Lucca, Figgo…) — carte
« Importer des absences » : l'export des absences en CSV, Excel ou JSON.

- Colonnes reconnues par leur titre : **date de début / de fin** (ou un
  jour par ligne, comme l'API Lucca : les jours se suivant — un week-end
  entre deux ne coupe pas — sont regroupés en une absence), **compte /
  type d'absence**, **statut**, **collaborateur**, commentaire.
- Le type décide : congés payés, congé familial… → **Congés** ; RTT,
  récupération, repos compensateur → **Repos** ; maladie, arrêt →
  **Arrêt maladie** ; accident (de travail, de trajet) → **Accident du
  travail** ; maladie professionnelle ; sinon **Autre** (le nom d'origine
  en cause). Le nom d'origine est gardé dans la note (« Import : RTT »).
- Refusées et annulées : ignorées ; en attente : importées avec la
  mention « en attente de validation ». Télétravail, formation,
  déplacement, mission : du travail, pas une absence — ignorés.
- Export d'un manager (plusieurs personnes) : la personne ayant le plus
  de lignes est proposée, choisissez-vous dans la liste.
- Une absence du même type couvrant déjà ces jours n'est pas ajoutée
  deux fois.

- Les colonnes sont reconnues **par leur titre**, en français ou en
  anglais (heure de début / fin, date, heure, montant, devise, lieu ou
  enseigne, articles, statut, n° de commande) ; l'aperçu dit quelle
  colonne a servi à quoi (« début : « Begin Trip Time » »).
- Les heures avec fuseau (« 2026-03-02 22:40:00 +0000 UTC » chez Uber)
  sont converties ; sans fuseau, c'est votre heure locale. Une ligne
  sans heure (note de frais, hôtel) garde sa date seule (heure
  « inconnue » : elle ne compte pas comme trace tardive et se complète
  par le reçu).
- Les lignes **annulées** sont ignorées ; les articles d'une même
  commande n'en font qu'une (prix compté une fois) ; une trace déjà
  enregistrée (même type, même minute, même montant) n'est pas
  réimportée.
- « Ajouter les repas livrés au Journal » crée un repas par commande,
  avec son prix, lu par l'IA.

Où trouver ces historiques (en général) :

| Source | Comment l'obtenir |
|--------|-------------------|
| Uber, Uber Eats | Application › Compte › Confidentialité › télécharger vos données : un ZIP avec un CSV des courses (`trips_data`) et des commandes Uber Eats. |
| Navigo / transports | Historique de validations du passe (espace personnel Navigo ou demande RGPD à Île-de-France Mobilités). |
| Parkings (Indigo, Onepark, Zenpark, PayByPhone…) | Historique ou factures dans le compte de l'application. |
| Taxis (G7…), hôtels | Reçus et factures (mails) : à ajouter en traces avec le fichier. |
| Notes de frais | L'export Excel du tableau de frais. |
| Banque | Export CSV du relevé : les paiements par carte (UBER EATS, parking, taxi…) avec date et montant. |

**Fichier de pointages en texte libre** (une ligne = un pointage ou une
journée, les mots disent ce qu'est chaque heure) :

| Exemple | Lu comme |
|---------|----------|
| `Date;Embauche;Débauche` puis `02/03/2025;08:12;17:30` | l'en-tête nomme les colonnes |
| `02/03/2025 08:12 17:30` (sans mot) | deux heures = embauche puis débauche (quatre = deux sessions) |
| `Embauche le 2 mars 2025 à 08:12` / `Débauche le 2 mars 2025 à 17:31` | une ligne par pointage (Raccourci iOS) |
| `Arrivée au travail, 3 mars 2025 à 07:58` / `Départ …` | arrivée, entrée, début, in, start… / départ, sortie, fin, out, end… |
| `2025-03-04T08:05:00+01:00 in` | date-heure ISO (avec ou sans fuseau) |
| `06/03/2025;22:00;06:00` | nuit : la débauche passe au lendemain |
| `[{"date": "2025-03-09", "embauche": "08:00", "debauche": "16:00"}]` | JSON : un enregistrement par ligne, les clés nomment les heures |
| `total 8h30`, `pause 00:45` | durées : ignorées |

Les heures sans fuseau sont celles de votre fuseau (Europe/Paris par
défaut). Une embauche sans débauche (ou l'inverse) devient une session à
compléter.

## Dossier

- **À confirmer — lu dans vos documents** : diagnostics et médicaments que
  l'IA a lus dans vos comptes-rendus / ordonnances (le nom figure dans le
  document) et que vous n'avez pas encore déclarés. « Ajouter aux
  maladies / traitements » les crée avec la mention du document source ;
  rien n'est ajouté sans vous.
- **Résultats d'examens** : chaque analyse (biologie, FibroScan) avec
  dernier résultat, précédent, évolution, historique et le document dont
  elle vient. Clic sur le nom → la courbe dans Données.
- **Chronologie** : documents, diagnostics, débuts / arrêts de traitement,
  rendez-vous.
- **Ajouter un document médical** : ordonnance, imagerie, compte-rendu,
  prise de sang, EFR, test de marche, vaccination… (PDF ou image).
- **Documents** : « Analyser (IA) » / « Réanalyser (IA) » un document,
  « Analyser tous les documents (IA) ». Sous chaque document : statut de
  lecture, valeurs vérifiées enregistrées, « Résumé IA (non vérifié) »,
  médicaments et diagnostics lus, **propositions rejetées** avec leur raison
  (voir le [guide IA](ia-medicale.md)).
- **Analyser une prise de sang (PDF)** : lecteur exact des comptes-rendus de
  laboratoire (valeurs actuelles + antériorités), sans IA.
- **Importer un dossier CDA** (Mon espace santé, médecin) et **visionneuse
  DICOM** (fichiers `.dcm`).

## Photos

- **Évolution** : protocole de prise de vue, marqueurs cliniques validés
  (FibroScan CAP / E, tour de taille / taille, IMC, FLI, FIB-4, HbA1c,
  glycémie, TyG) avec le formulaire tour de taille, taille, année de
  naissance, FibroScan ; suivi du poids (paliers 5 / 7 / 10 / 15 %) ;
  évolution par angle ; avant / après ; « Réanalyser tout l'historique ».
- **Galerie** : photos par angle (face / profil / dos), suppression.
- **Envoi des photos** : pas de bouton dans le site — les photos arrivent
  par `POST /api/v1/ingest/photo` avec un jeton `ingest:photo`
  (Raccourci iPhone, script) :

  ```bash
  curl -s $BASE/ingest/photo -H "Authorization: Bearer $PHOTO_TOKEN" \
    -F file=@face.jpg -F angle=face -F date_key=2026-09-22 -F weight=104.5
  ```

  `angle` : `face`, `profil` ou `dos` ; `date_key` et `weight` facultatifs.

## Suivi

- **Suivi par maladie** : chaque maladie déclarée avec ses indicateurs
  (dernière valeur, évolution, courbe) et les documents qui la mentionnent.
  Le lien se fait par mots-clés du nom : stéatose / foie gras / MASLD →
  FibroScan, ALAT, ASAT, GGT, triglycérides, poids, tour de taille ;
  diabète → HbA1c, glycémie ; tabac → cigarettes, souffle, SpO2 ;
  hypertension, apnée du sommeil, dyslipidémie, reins, anémie, thyroïde…
  Un nom inhabituel peut n'avoir aucun indicateur.
- **À confirmer**, **Maladies**, **Traitements** (arrêter / reprendre),
  **Rendez-vous** (saisie ou import `.ics`).

## Rapports

- **Synthèse clinique IA + PDF clinique** (par défaut) : le modèle médical
  rédige une synthèse de tout le dossier, chaque phrase citant ses faits ;
  affichée sur la page et en tête du PDF. Prend quelques minutes.
- **PDF clinique**, **Heures travaillées**, **Dossier travail ↔ santé**,
  **CSV**, **JSON**, **Excel**, **FHIR**.
- **Période** de chaque rapport : « Tout » par défaut, un raccourci ou
  deux dates exactes (Du … au …) ; la liste des rapports rappelle la
  période de chacun.
- **Exporter mes données** : tout l'historique au format choisi.

## Import

- **Importer mes données Apple Santé** : `export.zip` complet (Santé ›
  photo de profil › Exporter toutes les données). Rejouable sans doublon.
- **Synchro iPhone (export CSV)** : URL d'envoi pour SimpleHealthExportCSV.
- **Health Auto Export (JSON)** : URL de synchro quotidienne — voir le
  [guide d'ingestion](ingestion.md#health-auto-export-json).
- **Jetons d'accès (API)** : créer / révoquer des jetons et choisir leurs
  droits (voir le [guide de configuration](configuration.md#jetons-daccès-api)).

## Parcours types

| Je veux… | Faire |
|----------|-------|
| Tout mon historique Apple | Import › Apple Santé (`export.zip`), puis Données › Réconcilier. |
| Une synchro quotidienne | Import › Health Auto Export, coller l'URL dans l'app. |
| Ajouter une prise de sang | Dossier › Ajouter un document (Biologie) — l'IA la lit ; ou « Analyser une prise de sang (PDF) » pour le lecteur exact seul. |
| Ajouter un FibroScan | Dossier › Ajouter un document (Imagerie), ou Photos › Évolution › formulaire (CAP, E, date). |
| Une ordonnance → mes traitements | Dossier › Ajouter le document, attendre la lecture, puis « Ajouter aux traitements ». |
| Suivre une maladie | Suivi › déclarer la maladie (ou la confirmer depuis « À confirmer »). |
| Un rapport pour le médecin | Rapports › « Synthèse clinique IA » › Générer, puis Télécharger. |
| Compter eau, café, cigarettes, pipi | Raccourci iPhone : `POST /api/v1/sync/tally?token=<jeton>` avec `{"metric": "<clé>"}` ([Raccourcis iPhone](#raccourcis-iphone--une-seule-règle)). Par l'assistant MCP : « ajoute une clope » (outil `add_to_counter`, qui ajoute et n'efface jamais). |
| Noter un pipi | Journal › « Pipi maintenant », ou le Raccourci avec `{"metric": "elimination.urination"}`. |
| Noter un repas et savoir s'il était sain | Journal › Ajouter un repas (description + photo), ou le Raccourci repas › l'analyse s'affiche sous le repas. |
| Suivre mes heures de travail | Travail (ou Raccourci GPS `work.start` / `work.end`, ou l'assistant) ; heures sup et semaines > 48 h dans « Heures travaillées ». |
| Importer mes anciens pointages | Travail › Importer › Historiques de Raccourcis (tous les fichiers ensemble) › Lire › Importer. |
| Faire valoir un arrêt / un accident du travail | Travail › Dossier : compléter les journées, déclarer les arrêts et leur cause, ajouter les preuves (captures d'appels, mails), saisir les nuits manquantes, puis « Générer le rapport PDF complet ». |
| Vérifier que tout concorde | Données › Tout ce qui est enregistré. |
