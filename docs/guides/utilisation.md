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
- **Repas des 7 derniers jours**, groupés par jour avec le total du jour.

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
| Débauche | `work.end` (clôt la session ouverte) |

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
VFC ou de la tension.

- **Pointer** : « Embauche maintenant » / « Débauche maintenant », le
  Raccourci iPhone (même règle que les compteurs, voir plus haut, avec le
  GPS), ou l'assistant MCP (« j'embauche », « je débauche »). Une
  **session** va de l'embauche à la débauche ; plusieurs sessions par jour
  (pause déjeuner) s'additionnent. Une session appartient au jour où elle
  commence ; 24 h au plus ; deux sessions ne se chevauchent pas.
- **Valeurs du jour**, comme toute mesure (courbes, Données, tableaux de
  bord, exports, rapports) : `work.hours` (heures travaillées),
  `work.start` (première embauche) et `work.end` (dernière débauche), ces
  deux-là en heures décimales (8,25 = 08:15 ; 25,5 = 01:30 le lendemain).
- **Heures travaillées** sur 7 jours, 30 jours, 3 mois, 1 an ou tout :
  total, jours travaillés, moyenne par jour et par semaine, embauche et
  débauche moyennes, **heures supplémentaires** (par semaine, au-delà du
  contrat — 35 h par défaut, réglable), **jours de plus de 10 h** et
  **semaines de plus de 48 h** (maximums du Code du travail), plus longue
  journée ; graphique par semaine (vert : contrat, rouge : 48 h) et
  tableau court / moyen / long terme.
- **Exporter** la période par jour, semaine, mois ou session, en CSV,
  Excel ou JSON ; **Rapport PDF** (aussi dans Rapports › « Heures
  travaillées »).
- **Sessions (30 derniers jours)** : vérifier, ajouter une session oubliée
  (embauche + débauche), supprimer.
- **Importer d'anciens pointages** : un fichier txt, csv ou json. Il est
  d'abord **lu** (sessions trouvées, jours, heures, aperçu, lignes
  ignorées et pourquoi), puis importé sur « Importer ». Réimporter le même
  fichier ne crée pas de doublon (même début = même session).

Formats compris à l'import (une ligne = un pointage ou une journée) :

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
défaut). Une embauche sans débauche (ou l'inverse) est listée dans les
lignes ignorées ; ajoutez la session à la main si besoin.

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
- **PDF clinique**, **CSV**, **JSON**, **Excel**, **FHIR**.
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
| Importer mes anciens pointages | Travail › Importer d'anciens pointages › Lire le fichier › Importer. |
| Vérifier que tout concorde | Données › Tout ce qui est enregistré. |
