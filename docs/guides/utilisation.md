# Guide — utiliser le hub, page par page

Toutes les pages occupent **toute la largeur de l'écran** (une marge
qui suit sa taille) et s'adaptent au téléphone : en haut, une seule
ligne fine (Phoenix, thème, « ☰ page ouverte ») ; « ☰ » ouvre la grille
de toutes les pages avec le compte et « Déconnexion » — rien à faire
défiler de côté. Les boutons passent à la ligne, les onglets aussi ; le
Journal devient une fiche par jour. Les longues listes sont **paginées**
(« Par page », « Précédent / Suivant ») partout.

Si un **bloqueur de publicité / pistage** est actif (uBlock, AdGuard,
Brave, bloqueurs Safari), rien à régler : les requêtes du site évitent
les adresses que ces listes bloquent (`/api/v1/metrics…`, lue comme de la
télémétrie).

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

**Connexion** : une fois connecté, la session tient tant que la page
sert au moins une fois tous les 14 jours (`REFRESH_TOKEN_TTL_DAYS`) — le
jeton d'accès de 15 min est renouvelé tout seul, avant son échéance et
dès qu'une requête le trouve expiré (la requête est alors rejouée, sans
erreur à l'écran), y compris avec plusieurs onglets ouverts. Si la
session ne peut plus être renouvelée (déconnexion ailleurs, 14 jours
sans usage), la page de connexion le dit : « Session expirée :
reconnecte-toi ».

**Vos choix restent après un rechargement** (F5, retour sur la page, le
lendemain) : la **période** de chaque carte (Mes journées, Sessions,
Statistiques, Preuves et traces, Nuits, synthèse du dossier, Repas,
Rapports), l'**onglet** ouvert (Travail, Photos, tableaux de bord par
domaine) et les **filtres** (« Tous les jours », type de preuve,
recherche, niveau d'export, type de rapport). Une période qui allait
jusqu'à aujourd'hui (« 30 j », « Tout », « du 01/09 à aujourd'hui »)
avance avec les jours ; une période passée (« du 01/03 au 31/03 ») reste
telle quelle ; une période qui s'arrête avant aujourd'hui le dit (« La
période s'arrête le 08/09/2026 ») avec « Jusqu'à aujourd'hui ». Ces
choix sont gardés dans ce navigateur seulement.

## Accueil

**Récap du jour** : tuiles des mesures clés (dernière valeur, moyenne
7 j, évolution) — un clic ouvre la mesure dans **Données** avec son
graphique. Puis **Poids — tendance** : la courbe de `body.weight` par
Jour, Semaine, **Mois** (par défaut) ou Année, zoom à la molette,
« Tout (réinit. zoom) » pour revenir à l'ensemble ; dessous, la saisie
rapide « Poids du matin (kg) » › Enregistrer.

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

Signes vitaux (tendances : fréquence cardiaque, FC de repos, VFC, SpO2,
fréquence respiratoire, sommeil), séances, ECG (courbe, CSV), parcours
GPS (carte, GPX) — ces trois listes **paginées** — et observations du
dossier CDA importé (recherche, pages).

## Données

- **Tout ce qui est enregistré** : chaque métrique, ses relevés bruts et
  valeurs journalières par source avec leurs dates — c'est l'endroit pour
  vérifier que Apple, Health Auto Export et les labos concordent. Filtre
  et pages (25 par défaut).
- **Réconcilier et recalculer les valeurs journalières** : fusionne les
  clés en double, aligne les données sur le catalogue Apple, recalcule
  chaque valeur journalière depuis le brut. **Aucune IA.** Elle se lance
  **toute seule** à la fin de chaque import Apple Santé (`export.zip` ou
  zip SimpleHealthExportCSV) ; le bouton sert après une mise à jour du
  hub, ou pour tout recalculer à la main.
- **Une mesure en détail** : choisir une métrique → graphique + chiffres.
- **Données brutes** : relevés paginés, filtrables par métrique et dates.

## Journal

Un vrai journal de la journée : la nuit, l'eau, le café, les
cigarettes, le pipi, les médicaments et les repas.

Trois onglets (le dernier ouvert reste après un rechargement) :
**Aujourd'hui** (la nuit, les compteurs, les médicaments du jour, Mon
journal), **Repas** (le formulaire et la liste) et **Mes aliments**.

- **Aujourd'hui** : la nuit (« 6 h 40 de sommeil en 2 fois · 3 réveils ·
  23:40 → 06:50 », de la montre ou saisie dans Travail › Dossier travail
  et santé › Nuits), puis une tuile par compteur — **💧 Eau** (bouteilles
  de 1,5 L, affichées en litres), **☕ Cafés**, **🚬 Cigarettes**,
  **🚽 Pipi** — avec « +1 » et « − » (retire le dernier). Ce sont les
  mêmes compteurs que les Raccourcis iPhone (`/sync/tally`). Tant que
  rien n'est noté aujourd'hui, les tuiles Eau, Cafés et Cigarettes ont
  aussi un bouton **« 0 »** : il confirme une journée à zéro (sans lui,
  le jour compte « sans donnée » dans les rapports, pas zéro). Pour le
  pipi, « +1 » le note **maintenant** ; sous les tuiles : les heures des
  pipis du jour (× pour en retirer un) et **« Pipi à une autre heure »**
  (une heure d'aujourd'hui › Noter). Chaque miction est horodatée ; la
  valeur du jour (`elimination.urination`) est leur nombre — courbes,
  tableaux de bord, Suivi (diabète, apnée du sommeil) et rapports la
  voient comme toute autre mesure.
- **💊 Médicaments du jour** : chaque traitement actif (Suivi ›
  Traitements) avec « 1/2 aujourd'hui · dernier à 08:10 » et quatre
  boutons — **✔ Pris** (maintenant), **Pris à…** (une autre heure),
  **✗ Non pris** (oublié, refusé : le déclarer fait partie d'un relevé
  honnête), **↶ Annuler** (retire la dernière prise notée du jour).
  Chaque prise garde **l'heure de prise**, **l'heure de saisie** et **le
  canal** (site, raccourci iPhone, MCP) : une prise tapée des jours plus
  tard se voit comme telle. C'est la preuve de l'observance — voir
  Suivi › Traitements et les rapports.
- **Mon journal** : **une ligne par jour** (30 jours par défaut, ou « 7 j
  … Tout », dates exactes ; la période reste après un rechargement) —
  sommeil, **en combien de fois** (morceaux séparés d'une heure ou plus
  d'éveil), **réveils**, coucher → lever, eau, cafés, cigarettes, pipi,
  repas (nombre et kcal lues par l'IA), **médicaments** (prises notées,
  « non pris » déclarés) ; les moyennes de la page en tête.
  Paginé (50 par page, 10 sur téléphone, où chaque jour devient une
  fiche).
- **Ajouter un repas (suivi santé)** — jamais une preuve de travail, sans
  prix ; une note de frais (reçu, livraison) s'ajoute comme preuve dans
  Travail et son repas arrive ici marqué « 🧾 Note de frais » :
  type (petit-déjeuner, déjeuner, collation, dîner),
  date et heure, **description** (quantités, cuisson, « sans huile ni
  beurre »…), **aliments de ma liste** (facultatif : un aliment de « Mes
  aliments » — le menu montre nom · marque · poids · portion — et les
  grammes mangés, vide = lus dans la description, sinon votre portion
  habituelle, sinon estimés ; **« ▥ Scanner un
  code-barres »** photographie le paquet — appareil photo ou galerie —
  et choisit l'aliment de la liste qui porte ce code, reste à mettre
  les grammes puis « Ajouter ») et jusqu'à **7
  photos** : « 📷 Prendre une photo » (l'appareil photo, une à la fois)
  ou « 🖼️ Galerie » (plusieurs d'un coup, par exemple celles d'hier). La
  **première est l'assiette**, les suivantes l'emballage : la boîte, le
  sachet, le tableau des valeurs nutritionnelles — l'IA y **lit
  l'étiquette**. Chaque aperçu a son « × ». Les photos sont nettoyées
  (EXIF et GPS retirés), redimensionnées (2048 px pour l'emballage, pour
  que les petits caractères restent lisibles) et chiffrées si le
  chiffrement est activé.
- **Analyse du repas** (une à quelques minutes) — **l'IA reconnaît et
  pèse, les tables comptent** : l'IA liste les aliments et leurs
  grammes, puis les **valeurs** viennent, dans cet ordre :
  1. **vos aliments** (« Mes aliments ») : choisis dans le formulaire ou
     **nommés dans la description** — leur nom, un de leurs autres noms,
     ou **un mot de leur nom avec ce qui le confirme** : « un pavé de
     saumon » suffit pour « Saumon sauvage rose » si sa fiche a l'unité
     « pavé », « petite boîte d'aubergines » pour « Aubergines
     cuisinées à la provençale » (la boîte, ou la marque, confirme).
     Rien n'est deviné : « filet de poulet » ne prend pas « Poulet
     basquaise », « 2 pommes » ne prend pas « Pommes rissolées », et
     deux fiches possibles (« une barquette de poulet » avec « Poulet
     basquaise » et « Risotto au poulet ») = aucune. Pour être sûr :
     les **autres noms** de la fiche (« saumon, pavé de saumon »), ou
     choisir l'aliment dans la liste. Calculés avec **leur fiche** ; leurs
     **grammes sont lus par le code** dans la description : « 100g »,
     « 150 g de riz », sinon un compte × le poids de leur unité
     (« 2 tomates » = 2 × 120 g, « un demi concombre », « une tranche de
     comté », « ½ sachet de riz » = ½ × le paquet, « une boîte » ou
     « petite boîte » = la boîte : remplissez « Poids de la boîte » sur
     la fiche, sinon l'IA estime) — marqués
     « étiquette 🏷️ » ;
  2. la **table Ciqual 2025 de l'ANSES** (≈ 3 500 aliments génériques,
     embarquée dans le hub, rien n'est envoyé dehors) : l'IA choisit la
     référence la plus proche (même aliment, même cuisson) dans une
     courte liste tirée de vos mots, le code prend ses valeurs pour les
     grammes — marqués « Ciqual » ;
  3. sinon l'**estimation de l'IA**, contrôlée (marquée « estimé »).

  Chaque aliment dit **d'où viennent ses grammes** : « 240 g écrits »
  (dans la description : pesé, c'est exact), « 240 g comptés » (« 2
  tomates » × l'unité de la fiche), « 185 g, ta portion », « 125 g
  saisis » (formulaire), « 185 g, le paquet », « 400 g estimés par
  l'IA ». Pour qu'aucune quantité ne soit estimée : écrire les grammes
  (balance) ou avoir une fiche avec son unité.

  Puis les **nutriments** (énergie, protéines, glucides dont sucres,
  lipides dont saturés, fibres, sodium), une **note 0–10**, un verdict,
  les points positifs et à surveiller **pour vos maladies déclarées** —
  écrits par l'IA **après** le calcul, d'après ces chiffres exacts ; un
  chiffre cité dans une remarque qui n'est pas celui calculé pour
  l'aliment dont elle parle (ou le total du repas quand elle parle du
  repas) est retiré par le code.
  **Le même repas donne les mêmes chiffres** dès que ses aliments sont
  dans vos fiches ou dans la table ; seul l'avis (texte, note) peut
  varier si la description change de mots. Plus de « vérifier la
  composition du sachet ». Voir le [guide IA](ia-medicale.md#repas).
- Les nutriments d'un repas rejoignent les **mêmes mesures nutrition
  qu'Apple Santé** (`nutrition.energy`, protéines, glucides…) ; modifier,
  réanalyser ou supprimer le repas remplace ou retire exactement ses
  nutriments.
- **Repas** de la période (7 jours par défaut, ou dates exactes), groupés
  par jour avec le total du jour, 10 jours par page ; les photos de
  l'emballage en vignettes sous la description (un appui les agrandit).
  **« Modifier »** ouvre le repas en place : type, date et heure,
  description, aliments de ma liste, et ses **photos** — « × » en retire
  une (celle de l'assiette aussi), « 📷 Prendre une photo » /
  « 🖼️ Galerie » en ajoute après coup (un repas sans photo d'assiette
  prend la première ajoutée comme assiette, les suivantes comme
  emballage). « Enregistrer et réanalyser » applique tout puis relit le
  repas **une seule fois** ; ses nutriments sont remplacés.
  **« Refaire ce repas »** remplit le formulaire avec son type, sa
  description et ses aliments (on ajuste l'heure, on enregistre). Cocher
  des repas (ou « Tout sélectionner » : tous ceux de la période) puis
  « Supprimer la sélection » les retire d'un coup, avec photos et
  nutriments.
- **Mes aliments** : ce que vous mangez souvent — boîtes et sachets,
  mais aussi tomate, comté, pavé de saumon… **Une fiche remplie une
  fois** : nom, marque, **autres noms** utilisés dans un repas (« riz
  sachet, riz micro-ondes », séparés par des virgules), **poids de la
  boîte ou du sachet**, **unité et poids d'une unité** (« tomate » =
  120 g, « tranche » = 30 g, « pavé » = 125 g : c'est ce qui rend
  « 2 tomates » identique à chaque repas), **valeurs pour 100 g**
  (énergie, protéines, glucides dont sucres, lipides dont saturés,
  fibres, **sel** tel qu'imprimé : converti en sodium), **ma portion
  habituelle** (ce que vous en mangez d'habitude, en grammes ; sous le
  champ, « Toute la boîte », « ½ », « ¼ » la calculent depuis le poids
  de la boîte), une note (préparation, ce qu'il y a dedans) et la
  **source** des valeurs.

  **Une fiche par format** : la petite boîte (185 g) et la grosse du
  même produit sont **deux fiches**, chacune avec son poids, son
  code-barres (il change avec le format) et sa portion — par exemple
  « toute la boîte » pour la petite, « ¼ » pour la grosse. Partout (la
  liste, le choix dans un repas, l'analyse), une fiche s'affiche
  **nom · marque · poids**, suivi de sa portion dans le menu d'un repas
  (« Aubergines cuisinées à la provençale · Marque test · 185 g —
  portion : tout (185 g) ») : deux formats ne se confondent jamais. Dans
  une description, « petite boîte d'aubergines » prend la plus petite,
  « grosse (ou grande) boîte » la plus grande, « boîte de 750 g » celle
  de ce poids ; « boîte d'aubergines » seule ne choisit pas (l'analyse
  prend alors la table Ciqual : précisez, ou choisissez la fiche dans
  la liste). Les grammes, dans l'ordre : ceux du formulaire, ceux de la
  description (« un quart de la grosse boîte » = ¼ × 750 g, « 2 pavés »
  = 2 × l'unité), sinon **votre portion habituelle** (« petite boîte
  d'aubergines » sans nombre = votre portion de la petite boîte), sinon
  une boîte, sinon l'estimation de l'IA.

  Pour remplir les valeurs :
  - « 🏷️ Photo des valeurs (lecture IA) » lit l'étiquette et
    pré-remplit (nom, marque, poids net, valeurs plausibles seulement) ;
  - « 🔎 Table Ciqual (aliment courant) » : chercher « tomate crue »,
    « saumon vapeur »… et toucher un résultat prend ses valeurs
    (source « Ciqual 2025 · code · nom ») ;
  - « ▥ Code-barres (scan ou saisie) » : **« 📷 Scanner le
    code-barres »** ouvre l'appareil photo, **« 🖼️ Photo du
    code-barres »** prend une photo déjà dans la galerie, ou l'on tape
    les 13 chiffres sous le code puis « Chercher ». Le code est **lu
    par le hub lui-même, hors ligne** (EAN-13, EAN-8, UPC ; photo
    nette, code entier dans l'image, penché ou à l'envers accepté) et
    la photo n'est pas gardée. Puis, dans l'ordre : un aliment de votre
    liste porte déjà ce code → son nom s'affiche (« déjà dans vos
    aliments ») ; sinon **Open Food Facts** propose nom, marque, poids
    et valeurs du produit — **désactivé par défaut** (le hub ne sort
    pas sur Internet) : l'administrateur l'active avec
    `FOOD_LOOKUP_ONLINE=true` ; seul le code-barres est envoyé ;
    collaboratif : vérifiez contre le paquet ; sinon le code est
    simplement inscrit sur la fiche, et l'on remplit les valeurs
    (étiquette, Ciqual). D'Open Food Facts, la fiche garde **tout ce
    que donne la page du produit** : les 8 valeurs (le sodium tel
    qu'indiqué, pas recalculé depuis le sel), et sous « Open Food
    Facts : Nutri-Score B · NOVA 3 · fruits et légumes 96 % » (un
    appui ouvre le détail) les ingrédients, allergènes et traces,
    additifs (E330…), repères (sel modéré, sucres…), autres
    nutriments pour 100 g (potassium, vitamines… quand la page les
    donne), labels, catégories, portion indiquée et le lien vers la
    page. La liste des aliments en montre le résumé ;
  - « 📦 Photo de la boîte » garde la photo de l'emballage ; si le
    code-barres y est lisible, il est inscrit sur la fiche (quand elle
    n'en a pas déjà un).

  On vérifie puis on enregistre. Chaque fiche est à son utilisateur
  seul.

  **Relire Open Food Facts sans ressortir le paquet** : une fiche qui
  a un code-barres a le bouton **« ↻ Open Food Facts »** ; il relit sa
  page par ce code et dit ce qui a changé (« Mis à jour : sodium,
  infos produit » ou « À jour : rien n'a changé »). **« ↻ Tout relire
  sur Open Food Facts »**, à côté de « + Ajouter un aliment », le fait
  pour toutes les fiches (une minute au plus ; au-delà, il dit combien
  restent : relancer). Sont remplacés : les valeurs que la page donne
  (une valeur absente de la page est gardée), les infos produit, le
  poids et la marque s'ils sont vides ; restent les vôtres : nom,
  unité, portion habituelle, autres noms, note, photos. **Tout seul**,
  chaque nuit (4 h 40 UTC), le hub relit les fiches dont la page a
  plus de 30 jours (`FOOD_REFRESH_DAYS`), quelques-unes à la fois. Les
  repas déjà analysés gardent leur lecture : « Réanalyser » applique
  les nouvelles valeurs. La date de lecture est dans le détail « Open
  Food Facts » (« Page lue le … »).

  **Sel et sodium** : la fiche se remplit avec le **sel** imprimé sur
  le paquet ; le hub l'enregistre en **sodium** (1 g de sel = 400 mg de
  sodium), comme les repas le comptent. La fiche l'écrit sous le champ
  (« Sel 0,76 g = sodium 304 mg pour 100 g ») et la liste aussi (« sel
  0,76 g (sodium 304 mg) »).

  **Stock** (bouton « Stock » d'une fiche) : une quantité — en
  boîtes (× le poids de la boîte), en unités (« 6 » tomates) ou en
  grammes — puis **« J'ai acheté »** (les courses), **« Il m'en
  reste »** (un inventaire : ce qu'il y a vraiment dans le placard) ou
  **« Jeté / donné »** (sorti sans être mangé). Ce que vous **mangez
  n'est jamais à saisir** : chaque repas analysé retire de lui-même
  les grammes de ses lignes « étiquette » ; modifier, réanalyser ou
  supprimer le repas corrige le stock d'autant. Ne comptent pas : un
  repas acheté (avec un prix : livraison, note de frais), un repas
  encore en analyse, ni un repas mangé avant le premier achat noté ou
  avant le dernier inventaire (déjà dedans). La fiche affiche
  « Stock : 370 g (2 × 185 g) » ; « épuisé — les repas dépassent de
  … g » veut dire que les repas ont pris plus que ce qui a été noté :
  un « Il m'en reste » remet le compte juste. Sous les boutons,
  l'historique : achats, inventaires, pertes (× pour effacer une
  erreur) et repas qui ont pris dans le stock. Pour que le compte
  soit exact, pesez (une balance de cuisine) et écrivez les grammes
  dans le repas (« tomate 135 g »). « Que me préparer ce soir ? » :
  l'assistant MCP lit le stock (voir le [guide MCP](mcp.md)).

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
  facultatif : `1` par défaut, `-1` pour annuler un appui de trop, `0`
  pour **confirmer une journée à zéro** (eau, café, cigarettes, envies :
  « aucune aujourd'hui » est enregistré, au lieu d'un jour sans donnée) ;
  champ `date_key` (Texte, `AAAA-MM-JJ`) facultatif : aujourd'hui par
  défaut (heure locale), une autre date pour corriger un compteur passé.

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
| Débauche à distance | `work.remote_end` (même effet que `work.end` ; sans session ouverte, garde une débauche seule marquée « à distance ») |

Le pipi et le pointage se notent **maintenant** : pour eux, `date_key`
ne peut être qu'aujourd'hui, et le pointage n'accepte que `amount` = 1
(une autre heure se corrige dans Travail ; un pipi d'une autre heure :
Journal › « Pipi à une autre heure »).

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

### Noter une prise de médicament

Même jeton (`write:measurements`). Un raccourci par médicament (ou un
menu) :

- Action **« Obtenir le contenu de l'URL »**
- URL : `https://<hub>/api/v1/medications/take?token=<jeton>`
- Méthode **POST**, corps **JSON** : `treatment` (Texte) = le nom du
  traitement tel que dans Suivi › Traitements (majuscules et accents
  ignorés ; le début d'un mot suffit : « parox »), et facultatifs
  `taken_at` (Texte, ISO : une autre heure), `status` (`skipped` = non
  pris), `note`.
- **Afficher la notification** « Prise notée ».

Automatisation possible : Raccourcis › Automatisation › « Heure de la
journée » (08:00) → « Demander avant d'exécuter » activé → le raccourci
ci-dessus : l'iPhone demande à 8 h, un appui note la prise **à l'heure
réelle**. Chaque prise garde l'heure de saisie et le canal
« raccourci ».

En ligne de commande :

```bash
curl -s -X POST "http://<hub>/api/v1/medications/take?token=$TOKEN" \
  -H 'Content-Type: application/json' -d '{"treatment": "Paroxétine"}'
```

Ailleurs : Journal › Médicaments du jour (site), outils MCP
`log_medication`, `medications_today`, `medication_intakes`,
`medication_adherence`, `delete_medication_intake`.

### Noter un repas : description + photo

Le seul autre chemin, parce qu'un repas transporte une photo — même jeton.
Il prend **la date et l'heure** : un repas d'hier se note après coup.

C'est le **suivi santé** (« j'ai mangé ça ») : ce repas ne devient
**jamais une preuve de travail** et n'a pas de prix. Une **note de
frais** (reçu, livraison, repas payé) est une autre chose, ajoutée
ponctuellement comme **preuve** dans Travail › Dossier travail et santé
(genre « Repas » ou « Livraison », montant, reçu) : « Ajouter au
Journal » (coché par défaut) crée alors aussi son repas ici, pour la
santé, marqué « 🧾 Note de frais ».

**L'appel** — `POST /api/v1/meals?token=<jeton>`, corps **Formulaire**
(`multipart/form-data`) :

| Champ | Type | Obligatoire | Valeur |
|-------|------|-------------|--------|
| `description` | Texte | l'un des deux | ce que tu as mangé : quantités, cuisson, « sans huile » (fait foi pour l'IA) |
| `file` | Fichier | l'un des deux | la photo de l'assiette (JPEG, HEIC, PNG… 15 Mo max par photo — `MAX_UPLOAD_MB` —, 25 Mo pour tout l'envoi ; EXIF et GPS retirés) |
| `photos` | Fichier(s) | non | jusqu'à 6 autres photos : la boîte, le sachet, le tableau des valeurs (sans `file`, la première sert d'assiette) |
| `foods` | Texte | non | aliments de « Mes aliments » : `[{"food_id": "…", "grams": 125}]` (un aliment nommé dans la description est reconnu sans ça) |
| `eaten_at` | Texte | non | vide = maintenant ; `2026-09-23T20:30`, `2026-09-23T20:30:00+02:00` ou `23/09/2026 20:30` (sans fuseau = heure locale) |
| `meal_type` | Texte | non | `breakfast`, `lunch`, `snack`, `dinner` ; vide = d'après l'heure (avant 10:30, 15:00, 18:00) |

Un champ laissé vide (pas de photo) compte comme absent. La
réponse (201) donne le repas : `date_key`, `meal_type`, `has_photo`,
`analysis_status` (`queued`). L'analyse IA (une à quelques minutes)
apparaît ensuite dans **Journal**.

**Le raccourci** (un seul, pour maintenant comme pour hier) :

1. **Demander une entrée** — type *Date et heure*, question « Heure du
   repas ? », valeur par défaut *Date actuelle* (on valide, ou on
   remonte à hier).
2. **Formater la date** — *Entrée fournie*, format *ISO 8601*, avec
   l'heure (donne `2026-09-23T20:30:00+02:00`).
3. **Demander une entrée** — type *Texte*, « Qu'as-tu mangé ? ».
4. **Choisir dans le menu** « Photo ? » :
   « Prendre une photo » → action *Prendre une photo* ;
   « Depuis Photos » → *Sélectionner des photos* avec **« Sélectionner
   plusieurs »** activé (l'assiette d'abord, puis la boîte, le sachet,
   les valeurs) ;
   « Sans photo » → action *Texte* vide.
5. *(facultatif)* **Choisir dans le menu** « Repas ? » : une action
   *Texte* par branche — `breakfast`, `lunch`, `snack`, `dinner`, ou
   vide pour « Selon l'heure ».
6. **Obtenir le contenu de l'URL** — URL
   `http://<hub>/api/v1/meals?token=<jeton>`, méthode **POST**, corps
   **Formulaire** : `description` (Texte = réponse de l'étape 3),
   `eaten_at` (Texte = *Date formatée*), `photos` (**Fichier** = *Menu
   « Photo ? »* : une ou plusieurs photos, la première est l'assiette),
   et si l'étape 5 existe `meal_type` (Texte = *Menu « Repas ? »*).
7. **Afficher la notification** « Repas noté, analyse en cours ».

En ligne de commande, le même appel :

```bash
curl -s -X POST "http://<hub>/api/v1/meals?token=$TOKEN" \
  -F description="2 œufs, pain complet, café sans sucre" \
  -F eaten_at="2026-09-23T20:30" -F meal_type=dinner -F file=@repas.jpg \
  -F photos=@sachet.jpg -F photos=@valeurs.jpg
```

Ailleurs : **Journal › Repas** dans le site (type, date et heure,
description, aliments de ma liste, photos) ; outil MCP `log_meal`
(`description`, `meal_type`, `eaten_at` ISO, `photo_base64`,
`more_photos_base64`, `foods`). Les fiches d'aliments : **Journal › Mes
aliments**, `GET/POST /api/v1/foods`, outils MCP `list_foods`,
`save_food`, `read_food_label`, `scan_barcode`, `add_food_photo`,
`delete_food`. Une note
de frais : `add_evidence` (MCP) ou Travail › Preuves (site).

### Scanner un produit : est-il dans mes aliments ?

Photographier le code-barres d'un paquet et savoir si sa fiche existe
(ou ce qu'Open Food Facts en dit, si l'administrateur l'a activé).
Rien n'est enregistré, la photo n'est pas gardée.

**L'appel** — `POST /api/v1/foods/scan?token=<jeton>`
(`write:measurements`), corps **Formulaire** : `file` (**Fichier** =
la photo). Réponse JSON : `barcodes` (les codes lus, `[]` si aucun),
`food` (votre aliment avec ce code, ou `null`), `product` (proposition
Open Food Facts, ou `null`), `note` (pourquoi rien n'a été trouvé).

**Le raccourci** :

1. **Prendre une photo** (ou **Sélectionner des photos**) — le
   code-barres entier, net, bien éclairé.
2. **Obtenir le contenu de l'URL** — URL
   `http://<hub>/api/v1/foods/scan?token=<jeton>`, méthode **POST**,
   corps **Formulaire** : `file` (Fichier = la photo).
3. **Obtenir la valeur du dictionnaire** `food` › `name` ;
   **Si** elle a une valeur → **Afficher le résultat** « Dans mes
   aliments : *Valeur* » ; **Sinon** → **Obtenir la valeur du
   dictionnaire** `barcodes` puis **Afficher le résultat** « Pas
   encore de fiche pour *Valeur* : Journal › Mes aliments ».

En ligne de commande :

```bash
curl -s -X POST "http://<hub>/api/v1/foods/scan?token=$TOKEN" \
  -F file=@code-barres.jpg
```

### Ranger les courses : scanner chaque produit

Au retour des courses, scanner le code-barres de chaque paquet l'ajoute
au stock de sa fiche (la fiche doit exister : la créer une fois dans
Mes aliments, en scannant le même code).

**L'appel** — `POST /api/v1/stock?token=<jeton>` (`write:measurements`),
corps **JSON** : `barcode` (le code), `packs` (nombre de paquets,
défaut 1) — ou `food` (le nom de la fiche, le début d'un mot suffit),
`units`, `grams`, `kind` (`purchase` par défaut, `out`, `count`).
Réponse : `move` (ce qui est noté, `said` : « 2 × 185 g ») et `level`
(`name`, `grams` restants). `404` : aucune fiche avec ce code ; `422` :
deux formats répondent au même nom (donner le code-barres).

**Le raccourci** :

1. **Scanner le code QR/code-barres** (action *Scan QR or Barcode*).
2. **Demander une entrée** — type *Nombre*, « Combien de paquets ? »,
   valeur par défaut `1`.
3. **Obtenir le contenu de l'URL** — URL
   `http://<hub>/api/v1/stock?token=<jeton>`, méthode **POST**, corps
   **JSON** : `barcode` (Texte = *Code QR/code-barres*), `packs`
   (Nombre = *Entrée fournie*).
4. **Obtenir la valeur du dictionnaire** `level` › `name`, puis
   **Afficher la notification** « Rangé : *Valeur* ».

Pour enchaîner les paquets, mettre les étapes 1 à 4 dans **Répéter**
(par exemple 20 fois) et arrêter avec « Annuler » au scan.

En ligne de commande :

```bash
curl -s -X POST "http://<hub>/api/v1/stock?token=$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"barcode": "2001234567893", "packs": 3}'
```

> Un raccourci déjà réglé sur `POST /api/v1/journal/urination?token=…`
> (sans corps : maintenant ; ou `{"at": "…"}` en ISO) continue de
> marcher : c'est la route de « Pipi à une autre heure » dans le Journal.
> Pour un nouveau raccourci, suivre la règle ci-dessus.

## Travail

Les heures de travail comme donnée de santé : amplitude, heures
supplémentaires et semaines chargées se lisent à côté du sommeil, de la
VFC ou de la tension — jusqu'à un dossier complet pour faire valoir un
arrêt, un accident du travail ou une maladie professionnelle. La page a
six onglets, du plus utile au plus rare :

- **Journées** (ouvert par défaut) : le pointage (embauche sur place / à
  distance, débauche) puis **Mes journées**, une ligne par jour, la plus
  récente en haut, dans l'ordre de la journée :

  | Jour | Nuit (avant) | Réveil | Embauche | Débauche | Travaillé | Coucher | Absence | Preuves | État |
  |---|---|---|---|---|---|---|---|---|---|
  | mar. 22/09 | 7 h 10 · 3 réveils | 06:50 | 08:40 | 22:45 | **12 h 15** (dist. 1 h 45) | 23:40 | | 1 ▾ | |

  La nuit est celle d'avant le jour (durée, réveils), le coucher celui du
  soir ; la débauche est la dernière de la journée (à distance
  comprise, « +1 » après minuit) ; « Arrêt ½ » pour une demi-journée ;
  le nombre de preuves se déplie (« Voir » / « Télécharger ») ; « à
  compléter » mène à l'onglet du même nom. Week-ends grisés, filtre (jours
  travaillés, à compléter, absences, avec preuves), période au choix, et
  en tête les totaux : jours travaillés, heures (dont à distance),
  sommeil moyen, journées à compléter.
- **À compléter (N)** : les journées incomplètes et « Corrigées à la
  main » (plus bas).
- **Sessions** : chaque session, à ajouter, modifier ou supprimer.
- **Statistiques** : heures travaillées, graphique par semaine, court /
  moyen / long terme, export et rapport PDF. Puis **Dépenses repas —
  Uber Eats et livraisons** : sur la période choisie (« 1 an » par
  défaut, ou dates exactes ; elle reste après un rechargement) et pour
  les livraisons (les commandes Uber Eats importées), les repas payés
  (reçus, restaurants) ou les deux — total dépensé, commandes, panier
  moyen, moyenne par mois, plus grosse commande, **commandes tard**
  (21 h – 5 h : nombre, part, montant) ; un graphique **par jour, semaine
  ou mois** (« Auto » selon la durée ; le détail en liste dessous) ;
  l'**heure de commande** (tard le soir en orange) ; les **établissements
  qui coûtent le plus** (commandes, total, part). Survoler une barre
  donne son montant et son nombre de commandes. Ce sont les preuves et
  traces (notes de frais), jamais les repas notés dans le Journal.
- **Dossier travail et santé** : synthèse, arrêts et absences, preuves
  et traces, nuits. Le rapport PDF a une section **« Journées les plus
  significatives »** (20 au plus, les plus marquantes d'abord) : date,
  arrivée, départ (« +1 » le lendemain), amplitude (et travail si des
  pauses), pourquoi — session continue de 24 h ou plus, amplitude > 13 h
  (repos de 11 h impossible), plus de 10 h de travail, samedi, dimanche
  ou jour férié travaillé, travail pendant un arrêt, fin après 21 h ou
  minuit — et les notes saisies sur les sessions du jour. Les tableaux
  du rapport passent à la ligne au lieu de déborder.
- **Importer** : historiques de Raccourcis, traces, absences, pointages.

**Périodes et pages, partout pareil.** Chaque liste ou calcul daté
(heures travaillées, sessions, synthèse du dossier, preuves et traces,
nuits, repas, rapports) a le même sélecteur : raccourcis **7 j**,
**30 j**, **3 mois**, **1 an**, **Tout** (depuis la première donnée), et
deux dates exactes **Du … au …** pour n'importe quelle période. Les
listes longues se lisent **page par page** : « Par page » (10 par
défaut, ou plus) et « Précédent / Suivant ». Les jours s'entendent à
l'heure locale : un taxi à 00:30 compte pour ce jour-là.

### Pointage (onglets Journées, À compléter, Sessions, Statistiques)

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
- **Journées à compléter** : toutes les sessions incomplètes, avec
  « **preuve présente** » ou « sans preuve » et un filtre (avec / sans
  preuve, embauche ou débauche manquante), en deux vues :
  - **Calendrier** (par défaut) : 12 mois d'un coup d'œil (« ◀ 12 mois »,
    « Aujourd'hui », « 12 mois ▶ »), une **pastille** par jour à
    compléter — **rouge** sans preuve, **orange** preuve présente — et le
    nombre par mois ; un point vert pour une journée complète, gris pour
    une absence ou un férié. **Cliquer un jour** ouvre sa fiche **à
    droite** (la même que dans la liste), avec « ← Jour précédent /
    Jour suivant → » parmi les jours à compléter. Le mois et le jour
    choisis restent après un rechargement. Le calendrier suit la largeur
    de l'écran : 6 mois par ligne sur un grand écran, 4, 3 ou 2 sur un
    plus petit ; sur téléphone la fiche passe sous les mois et s'affiche
    dès qu'on touche un jour.
  - **Liste** : les fiches l'une sous l'autre, page par page.

  Chaque journée est une fiche : ce qui est connu (« Embauche 08:40 · Débauche
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
- **Autres sessions du jour et chevauchements** : en tête de chaque fiche,
  « Autres sessions ce jour-là » montre ce que la journée contient déjà
  (« 09:02 → ? — embauche seule », « 09:02 → 12:30 »), car une heure ne
  peut pas chevaucher une autre session.
  - Une **embauche seule** et une **débauche seule** du même jour (jamais
    appariées, par exemple quand la débauche a été enregistrée avant
    l'embauche) : « **Réunir : 09:02 → 19:12** » en fait une seule
    session (première embauche → dernière débauche), l'autre est
    supprimée et la note garde ce qu'elle contenait (« réunie avec 09:02
    → ? »). Même lieu seulement (sur place avec sur place).
  - Compléter une session en englobant une embauche ou une débauche seule
    du même lieu la **réunit d'office** (« ? → 19:12 » complétée à 08:55
    avec une embauche seule à 09:02 : 08:55 → 19:12, note « embauche
    seule de 09:02 réunie »).
  - Une session complète avant (le matin 09:02 → 12:30) : « **Embauche
    après elle : 12:30** » pré-remplit la limite ; « Réunir » en fait une
    seule session sans pause si la coupure n'en était pas une.
  - Le message d'erreur nomme la session gênante : « Chevauche la
    session du 02/03/2026 09:02 → 12:30 : choisis une heure en dehors, ou
    réunis les deux sessions ».
  - Dans « **Modifier** » une session, les sessions que les heures tapées
    chevauchent s'affichent en direct, avec leur note, et « **Réunir :
    02/04 12:01 → 03/04 21:22** » : une session continue de 33 h 21 se
    saisit en étirant celle du 03/04 jusqu'au 02/04 12:01, puis en la
    réunissant avec celle du 02/04 (les heures tapées sont gardées ; la
    note garde ce que l'autre contenait). Une session finie un autre jour
    affiche ce jour dans la liste (« 21:22 (03/04) »).
- **Ajouter une preuve après coup**, là où il en manque une : « **+
  Ajouter une preuve pour ce jour** » sur chaque journée à compléter,
  dans « Mes journées » (le bouton « + » de la colonne Preuves, ou sous
  les preuves dépliées) et dans « Modifier » une session ; « + Ajouter
  une preuve à cette absence » sur chaque arrêt ou absence (la preuve y
  est rattachée). Le formulaire est celui de « Preuves et traces », daté
  du jour (à midi, à ajuster) ; un fichier nommé avec sa date et son
  heure remplit « Quand » tout seul. La preuve apparaît aussitôt dans la
  journée, avec « Prendre 08:47 ».
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
- **Pointages du jour** : sous les boutons d'embauche et de débauche,
  la carte « Travail — aujourd'hui » liste les pointages du jour
  (« À distance 21:45 → en cours ») avec « **Supprimer** » : un clic de
  trop ou un essai s'annule là, après confirmation.
- **Sessions** de la période (30 jours par défaut), page par page, avec
  un filtre (corrigées à la main, à distance, incomplètes), en tableau
  (jour, embauche, débauche, durée, lieu, origine) : vérifier,
  « **+ Ajouter une session** » oubliée dans un cadre à part (embauche,
  débauche — vide : à compléter —, lieu sur place ou à distance),
  **modifier** (heures, lieu, note, avec les preuves du jour),
  supprimer (après confirmation), ou en cocher plusieurs pour les
  supprimer d'un coup (voir « Supprimer plusieurs éléments à la fois »).
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
  capture), titre, description, fichier (**25 Mo** au plus par envoi : la
  limite du proxy nginx, plus basse que les 30 Mo de l'API ; chiffré au
  repos si activé). **Traces** — ce que des tiers ont enregistré :
  transport (métro, Navigo, train), taxi / VTC, parking, **repas livré**
  (Uber Eats…), repas acheté, hôtel, note de frais, **activité pro**
  (tickets traités, messages, outils : créée surtout par l'import des
  tickets et des conversations WhatsApp, voir Importer) — avec en plus
  l'heure de **fin** (sortie du parking, arrivée du taxi, départ de
  l'hôtel), le
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
  filtre par période, par type (preuves, traces, ou un type précis) et
  par **mots** (titre, lieu, détail, nom du fichier), la plus récente
  d'abord, page par page.
- **Supprimer plusieurs éléments à la fois** — preuves et traces,
  sessions, arrêts et absences, repas du Journal : cocher les éléments,
  ou « **Tout sélectionner** » (tous ceux que la période et les filtres
  affichent, **toutes pages comprises**), puis « **Supprimer la
  sélection (N)** » ; une confirmation rappelle combien partent, c'est
  définitif. Un élément coché puis masqué par un filtre n'est pas
  supprimé. Pour des traces de repas livrés, « et les N repas du
  Journal créés par ces livraisons » (coché par défaut) retire aussi ces
  repas. Les journées des sessions supprimées sont recalculées. Exemple :
  des courses importées avant la lecture exacte des exports Uber (lieu
  « Paris », 0 €) : type « Taxi / VTC », chercher « Personal », « Tout
  sélectionner », supprimer, puis réimporter le fichier.
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
deviné du nom : `trips` → taxi, `eats`, `user_orders` → repas livré,
`navigo` →
transport…), « Lire », puis « Importer ». Un envoi fait **25 Mo** au
plus, tous fichiers ensemble (limite du proxy nginx) : importer un gros
lot en plusieurs fois.

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
- **Uber (courses) et Uber Eats** : les fichiers de « Télécharger mes
  données » sont lus colonne par colonne, sans rien deviner.
  - `rider_lifetime_trips-0.csv` : une trace **Taxi / VTC** par course
    faite, de la **prise en charge** au **dépôt**, aux heures exactes
    (colonnes `_utc` : les colonnes `_local` sont des heures locales
    marquées à tort « Z », elles décaleraient d'1 ou 2 h). Titre :
    « Uber UberX : adresse de départ → adresse d'arrivée » telles
    qu'Uber les a écrites ; lieu : l'adresse de départ. Détails : heure
    de la demande, de la prise en charge et du dépôt, distance (km) et
    durée, **prix payé** (celui affiché à la réservation, remise
    déduite ; « avant remise » s'il diffère), pourboire à part, « profil
    pro » pour un profil Business, points GPS du départ et du dépôt
    réel. Les demandes **annulées** ou **sans chauffeur** ne sont pas
    des courses : non importées, listées dans l'aperçu avec l'heure et
    les adresses (« course annulée par toi — demandée le 05/02/2026
    21:15 : … »).
  - `user_orders-0.csv` : une ligne par article ; les lignes d'une
    même commande (même établissement, même heure) font **une trace
    Repas livré** : l'**établissement**, l'heure de **commande** et
    celle de **livraison**, les articles (« 2× Pizza 4 fromages,
    Nuggets (15 pièces, Ketchup) ») et le **prix de la commande**. Le
    repas ajouté au Journal prend l'heure de livraison. Les commandes
    annulées sont ignorées.
  - La colonne ville (`city_name`, `City_Name`) est la **zone du compte
    Uber** (« Paris » pour un établissement à 60 km de Paris) : elle n'est
    jamais prise pour le lieu.
  - L'aperçu montre les premières traces telles qu'elles seront
    enregistrées et, dépliables, les lignes non importées avec la
    raison.
- **Conversations WhatsApp** (export `.txt` d'une discussion) : iPhone
  (`[23/05/2025 21:56:42] Nom : message`) comme Android (`23/05/2025
  21:56 - Nom: message`, ou `5/23/25, 9:56 PM`), un message sur
  plusieurs lignes compris. Pour chaque jour de la conversation :
  - **vos messages** font une trace **Activité pro**, de votre premier à
    votre dernier message du jour (« WhatsApp — Alex : 5 messages de
    moi, 3 reçus », 22:10 → 23:40) : elle compte comme présence (jour
    travaillé sans pointage, traces tardives, repères des journées à
    compléter), y compris **pendant un arrêt** (le rapport liste les
    preuves datées pendant chaque arrêt) ;
  - un **appel décroché** (« Appel vocal 3 min », « Appel vidéo 1 h 5
    min ») compte aussi dans cette activité, jusqu'à sa fin (21:29 + 3
    min → 21:32) ;
  - un jour avec seulement des **messages reçus** : une preuve « SMS /
    message » ; tous les **appels** (vocal, vidéo, manqué) font aussi une
    preuve « Appel » avec leur nombre et leur durée (« 3 appels (1
    manqué), 1 h 08 » ; le rapport compte les appels pendant l'arrêt,
    dont le dimanche) ;
  - chaque jour liste ses messages (heure, auteur, texte) ; l'avis de
    chiffrement est ignoré ; le fichier `.txt` est gardé **intact**
    comme document (SHA-256).
  - **Qui êtes-vous** dans la conversation : « Moi » (ou « Me »,
    « Vous »…) si l'export l'écrit ainsi, sinon choisissez votre nom
    dans la liste de l'aperçu. Le nom de la conversation vient du nom
    du fichier (« Discussion WhatsApp avec Alex.txt ») ou de l'export.
  - Réimporter un export plus récent complète les jours (plus de
    messages) sans doublon.

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
| Uber, Uber Eats | Application › Compte › Confidentialité › télécharger vos données : un ZIP avec le CSV des courses (`rider_lifetime_trips-0.csv`, anciennement `trips_data`) et celui des commandes Uber Eats (`user_orders-0.csv`). |
| WhatsApp | Dans la discussion : iPhone › nom du contact › Exporter la discussion › Sans médias (un .zip : importer le `_chat.txt` qu'il contient) ; Android › ⋮ › Plus › Exporter la discussion › Sans médias (un .txt). |
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

Cinq onglets (le dernier ouvert reste) : **Synthèse** (à confirmer,
résultats d'examens), **Chronologie**, **Documents** (ajout + liste),
**Imagerie** (DICOM), **Importer** (prise de sang PDF, dossier CDA).

- **À confirmer — lu dans vos documents** : diagnostics et médicaments que
  l'IA a lus dans vos comptes-rendus / ordonnances (le nom figure dans le
  document) et que vous n'avez pas encore déclarés. « Ajouter aux
  maladies / traitements » les crée avec la mention du document source ;
  rien n'est ajouté sans vous.
- **Résultats d'examens** : chaque analyse (biologie, FibroScan) avec
  dernier résultat, précédent, évolution, historique et le document dont
  elle vient. Clic sur le nom → la courbe dans Données. Filtre, 25 par
  page.
- **Chronologie** : documents, diagnostics, débuts / arrêts de traitement,
  rendez-vous — paginée, avec un filtre (Tout, Documents, Diagnostics,
  Traitements, Rendez-vous, « Tout sauf les rendez-vous » quand un agenda
  importé noie le reste).
- **Ajouter un document médical** : ordonnance, imagerie, compte-rendu,
  prise de sang, EFR, test de marche, vaccination… (PDF ou image).
- **Documents** : recherche (titre, type, date), 10 par page ;
  « Analyser (IA) » / « Réanalyser (IA) » un document,
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
- **Galerie** : filtre Toutes / Face / Profil / Dos (gardé après un
  rechargement) ; chaque photo avec sa date, le poids lié, son statut
  (Reçue, Prête, Analysée, Qualité insuffisante, IA indisponible, Image
  illisible) et son analyse, puis deux boutons : **« Relancer
  l'analyse »** (remet cette photo dans la file du worker : préparation,
  contrôle qualité, analyse avec le modèle de vision actuel) et
  **« Supprimer »** (après confirmation). **« Tout supprimer »** (en haut,
  après confirmation) efface **toutes** les photos, quel que soit le
  filtre affiché.
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
- **Traitements** : nom, dose, fréquence et **prises / jour** (le nombre
  prévu : 1, 2, 3… ; vide = à la demande). Chaque traitement montre son
  **observance sur 30 jours** : « 30 j : 93 % (56/60) · 2 j sans rien
  noté · vers 08:10 » — prises notées ÷ prévues (chaque jour compté au
  plus pour ses prises prévues), jours sans aucune saisie, heure
  habituelle (médiane). Le détail (prises non prises, plus long trou,
  saisies en retard, par semaine) est dans `GET /medications/adherence`
  et les rapports. Les prises se notent dans Journal › Aujourd'hui ›
  Médicaments du jour, un raccourci iPhone ou MCP.
- **À confirmer**, **Maladies**, **Traitements** (arrêter / reprendre),
  **Rendez-vous** (saisie ou import `.ics`) : **À venir** (le plus proche
  d'abord) ou **Passés** (le plus récent d'abord), recherche (praticien,
  lieu), 10 par page. Un agenda importé en entier (des centaines
  d'événements personnels) se nettoie d'un coup : chercher, « Tout
  sélectionner » (toutes pages), « Supprimer la sélection ».

## Rapports

- **Synthèse clinique IA + PDF clinique** (par défaut) : le modèle médical
  rédige une synthèse de tout le dossier, chaque phrase citant ses faits ;
  affichée sur la page et en tête du PDF. Prend quelques minutes.
- **PDF clinique**, **Heures travaillées**, **Dossier travail ↔ santé**,
  **CSV**, **JSON**, **Excel**, **FHIR**.
- **Ce que le PDF clinique prouve** (et la synthèse, qui l'inclut) — des
  faits vérifiables, chacun avec ce sur quoi il est calculé :
  - **En-tête** : période, **numéro du rapport**, **date et heure de
    création** (fuseau), **version** du hub, **sources des valeurs**
    (Apple Santé, montre et compteurs, saisie, repas analysés…, avec
    leur nombre), **empreinte SHA-256 des données** utilisées. Chaque
    page porte en pied le numéro du rapport, sa date et « page n/N ».
  - **Habitudes enregistrées** (cigarettes, envies cassées, cafés, eau,
    mictions) : **jours saisis / jours de la période** (un jour sans
    saisie n'est **pas** compté zéro : il est « sans donnée » ; un vrai
    zéro se confirme avec le bouton **« 0 »** de la tuile dans Journal ›
    Aujourd'hui), total, moyenne par jour saisi, médiane, jour le plus
    bas et le plus haut (avec leur date) ; les **cigarettes jour par
    jour** (barres, trous = jours sans donnée) et **par semaine ou par
    mois** ; et, avec **« Comparer avant / après le »** (champ du
    formulaire), la moyenne **avant** et **depuis** cette date, avec le
    nombre de jours de chaque côté et l'évolution en %.
  - **Médicaments — observance** : par traitement, du … au …, prises
    prévues / prises / non prises, taux, jours sans aucune saisie et
    plus long trou, heure habituelle, prises saisies après coup.
  - **Alimentation** : repas, jours, types, part lue par l'IA, moyennes
    par jour (énergie, protéines, glucides, sucres, lipides, saturés,
    fibres, sodium), notes de l'IA, origine des valeurs (étiquette,
    Ciqual, estimé), vos aliments les plus mangés, par mois, repas saisis
    plus de 3 h après.
  - **Dossier de soins** : maladies, traitements **datés** (début → fin,
    prises/jour), rendez-vous **de la période** avec le praticien, les 30
    documents les plus récents ; puis courbes, tableaux par domaine et
    **réponses oui / non** (« N jours oui, M non, sur X saisis »).
  - **Traçabilité des saisies** (en fin de rapport) : pour chaque
    compteur, combien de saisies ont été faites **le jour même** ou
    **après coup**, par quel **canal** (site, raccourci) ; pour les
    prises et les repas, combien dans l'heure (3 h pour un repas), le
    jour même, plus tard. C'est ce qui montre qu'un relevé a été tenu au
    fil des jours.
- **Authenticité** : le hub garde l'**empreinte SHA-256 de chaque
  fichier** (affichée sous le statut : « empreinte 1a2b… ») et la note au
  journal d'audit. **« 🔏 Vérifier un fichier »** (sous la liste) dit si
  une copie reçue (par un médecin, un avocat, l'employeur) est
  **identique octet pour octet** à un de vos rapports, et lequel ; un
  fichier modifié ou venant d'un autre compte est refusé.
- **Heures travaillées / Dossier travail ↔ santé** : le champ **« Heures
  de contrat par semaine »** (35 par défaut) sert aux heures
  supplémentaires.
- Les mêmes faits en JSON : `GET /api/v1/facts?start=…&end=…&compare_from=…`
  (outil MCP `period_facts`) ; vérifier une copie : `POST
  /api/v1/reports/verify` (MCP `verify_report`).
- La **synthèse IA** porte sur tout le dossier (ses indicateurs comparent
  les 30 derniers jours aux 30 précédents) ; les sections factuelles
  ci-dessus portent sur la période choisie.
- **Période** de chaque rapport : « Tout » par défaut, un raccourci ou
  deux dates exactes (Du … au …) ; la liste des rapports rappelle la
  période de chacun.
- **Exporter mes données** : tout l'historique au format choisi.

## Import

- **Importer mes données Apple Santé** : `export.zip` complet (Santé ›
  photo de profil › Exporter toutes les données) ou `export.xml`, sans
  limite de taille. Rejouable sans doublon. Pendant l'envoi :
  « Téléversement… N % » ; puis la liste des **20 derniers imports**
  (statut `queued`, `running` avec l'étape et le nombre d'enregistrements
  lus — mise à jour toute seule —, `done` avec échantillons, séances,
  ECG et tracés, ou `error` avec la raison). La réconciliation
  (Données) suit d'elle-même chaque import réussi.
  **« Supprimer les données importées »** efface d'un coup tout ce qui
  vient de l'export Apple (relevés, séances, ECG, tracés GPS, dossier
  CDA), après confirmation (« ne peut pas être annulée ») ; les saisies,
  compteurs, repas, Health Auto Export et documents restent.
- **Synchro iPhone (export CSV)** : « Créer l'URL d'upload » crée un
  jeton `write:measurements` (« iPhone (CSV) ») et affiche une fois
  `…/api/v1/imports/apple-health?token=…`, à coller dans l'envoi du
  raccourci SimpleHealthExportCSV (champ Fichier `file` = le zip) ; la
  recette pas à pas est sur la carte.
- **Health Auto Export (JSON)** : URL de synchro quotidienne — voir le
  [guide d'ingestion](ingestion.md#health-auto-export-json).
- **Jetons d'accès (API)** : créer / révoquer des jetons et choisir leurs
  droits (voir le [guide de configuration](configuration.md#jetons-daccès-api)).

## Parcours types

| Je veux… | Faire |
|----------|-------|
| Tout mon historique Apple | Import › Apple Santé (`export.zip`) : la réconciliation suit toute seule à la fin de l'import. |
| Une synchro quotidienne | Import › Health Auto Export, coller l'URL dans l'app. |
| Ajouter une prise de sang | Dossier › Ajouter un document (Biologie) — l'IA la lit ; ou « Analyser une prise de sang (PDF) » pour le lecteur exact seul. |
| Ajouter un FibroScan | Dossier › Ajouter un document (Imagerie), ou Photos › Évolution › formulaire (CAP, E, date). |
| Une ordonnance → mes traitements | Dossier › Ajouter le document, attendre la lecture, puis « Ajouter aux traitements ». |
| Suivre une maladie | Suivi › déclarer la maladie (ou la confirmer depuis « À confirmer »). |
| Un rapport pour le médecin | Rapports › « Synthèse clinique IA » › Générer, puis Télécharger. |
| Compter eau, café, cigarettes, pipi | Raccourci iPhone : `POST /api/v1/sync/tally?token=<jeton>` avec `{"metric": "<clé>"}` ([Raccourcis iPhone](#raccourcis-iphone--une-seule-règle)). Par l'assistant MCP : « ajoute une clope » (outil `add_to_counter`, qui ajoute et n'efface jamais). |
| Noter un pipi | Journal › Aujourd'hui › tuile 🚽 Pipi › « +1 » (maintenant) ou « Pipi à une autre heure », ou le Raccourci avec `{"metric": "elimination.urination"}`. |
| Noter un repas et savoir s'il était sain | Journal › Ajouter un repas (description + photo), ou le Raccourci repas › l'analyse s'affiche sous le repas. |
| Suivre mes heures de travail | Travail (ou Raccourci GPS `work.start` / `work.end`, ou l'assistant) ; heures sup et semaines > 48 h dans « Heures travaillées ». |
| Importer mes anciens pointages | Travail › Importer › Historiques de Raccourcis (tous les fichiers ensemble) › Lire › Importer. |
| Faire valoir un arrêt / un accident du travail | Travail › Dossier : compléter les journées, déclarer les arrêts et leur cause, ajouter les preuves (captures d'appels, mails), saisir les nuits manquantes, puis « Générer le rapport PDF complet ». |
| Vérifier que tout concorde | Données › Tout ce qui est enregistré. |
