# Guide — l'IA médicale (MedGemma via Ollama)

L'IA tourne **localement** (Ollama sur votre machine) : aucune donnée ne
part sur Internet. Elle n'est **jamais** une source de vérité seule : chaque
valeur qu'elle propose est vérifiée contre le texte du document, et chaque
phrase de la synthèse doit citer les faits du dossier.

## Quel modèle pour quelle tâche

| Tâche | Variable | Modèle conseillé | Pourquoi |
|-------|----------|------------------|----------|
| Photos (face / profil / dos) | `OLLAMA_VISION_MODEL` | `medgemma1.5` (4B, image + texte) | Entraîné sur images médicales, comparaison dans le temps. |
| Lecture des documents (valeurs, dates) | `OLLAMA_DOCUMENT_MODEL` (vide = vision) | `medgemma1.5` | Meilleure extraction des comptes-rendus de labo, lit aussi les scans. |
| Résumé, médicaments, diagnostics, synthèse clinique | `OLLAMA_TEXT_MODEL` | `medgemma:27b` | Le raisonnement médical le plus solide. |
| Repas — photos et étiquettes (assiette, boîte, sachet, tableau des valeurs) | `OLLAMA_VISION_MODEL` | `medgemma1.5` | Voit toutes les photos d'un repas ensemble : aliments, portions, valeurs imprimées. |
| Repas — aliments et grammes, choix des références Ciqual, note 0–10, verdict | `OLLAMA_TEXT_MODEL` | `medgemma:27b` | Raisonne sur la description, vos aliments et vos maladies déclarées. |
| Lecture d'une étiquette (Journal › Mes aliments › « 🏷️ Photo des valeurs ») | `OLLAMA_VISION_MODEL` | `medgemma1.5` | Une photo, réduite à 2048 px ; tourne **dans l'API** (pas le worker), **100 s** au plus. |

Réglages communs : réponses JSON, température 0 et graine fixe (une même
entrée donne la même réponse), contexte 8192 jetons, **une requête à la
fois par processus** (Ollama sert les requêtes l'une après l'autre ; le
verrou est propre à chaque processus : l'API et le worker peuvent appeler
Ollama en même temps), 10 min maximum par appel.

## Lecture d'un document (Dossier › Analyser)

1. **Lecteurs exacts d'abord** (sans IA) : comptes-rendus de laboratoire
   (valeur du jour + antériorités avec leur date) et FibroScan (CAP en
   dB/m, élasticité E en kPa, poids / taille imprimés). La date retenue est
   celle de l'examen — jamais une date de naissance.
2. **Le modèle de document** propose les valeurs que les lecteurs n'ont pas
   trouvées (texte découpé en morceaux ; un scan est envoyé en images +
   OCR).
3. **Vérification** : une proposition n'est gardée que si la mesure est
   connue, l'unité correspond, et **le nombre et la date sont imprimés**
   dans le document. Sinon elle est **rejetée**, avec sa raison, visible
   sous le document :
   - `mesure inconnue` — pas une analyse suivie par le hub ;
   - `unité différente (attendu …)` ;
   - `nombre absent du document` — valeur inventée ou mal lue ;
   - `date absente du document` ;
   - `valeur ou date illisible`, `format invalide`.

   Des rejets sont normaux : c'est le filet qui empêche une erreur de l'IA
   d'entrer dans vos courbes.
4. **Le modèle texte** écrit le résumé en français et liste médicaments et
   diagnostics, à partir des seules valeurs vérifiées ; un nom qui ne figure
   pas dans le document est écarté. Ce résumé reste marqué **« non
   vérifié »**.
5. Les valeurs vérifiées rejoignent les mêmes métriques que toutes les
   autres sources (`bio.*`, `liver.cap`, `liver.lsm`, `body.*`) : marqueurs,
   courbes, Dossier, Suivi, rapports les voient aussitôt.

**Statuts** : en attente → lecture en cours → lu / échec (avec l'erreur).
Une lecture a **30 minutes** maximum ; un redémarrage du worker relance
les lectures interrompues. « Réanalyser » relit un document avec les
modèles actuels ; « Analyser tous les documents » les relit tous.

`GET /api/v1/medical/documents/{id}/text` (outil MCP `document_text`)
renvoie le texte exact que l'IA a lu — pour vérifier une extraction.

## Synthèse clinique (Rapports)

1. Tout le dossier devient une liste de **faits numérotés** (`F1`, `F2`…) :
   maladies, traitements, **observance des 30 derniers jours** (par
   traitement ayant des prises notées : prises notées sur prévues et taux,
   non prises déclarées, jours sans saisie, plus long trou, heure
   habituelle, saisies faites après coup), marqueurs avec leur
   interprétation, résultats d'examens avec la valeur précédente, poids
   (évolutions, perte depuis le pic), indicateurs Apple (30 derniers jours
   vs 30 jours avant et il y a un an), tendance des photos, documents.
2. Le modèle texte rédige : synthèse, évolutions, points d'attention, à
   discuter avec le médecin, données manquantes — **chaque phrase cite ses
   faits** (`[F3][F12]`).
3. **Contrôle** : une phrase sans référence, avec une référence inconnue,
   ou avec un **chiffre ou un code** (S3, HbA1c, F0-F1…) absent des faits
   qu'elle cite est **retirée** et listée avec la raison.
4. Résultat : sur la page Rapports (survol d'une référence = le fait cité)
   et en tête du PDF clinique, faits en annexe. Si le modèle est
   injoignable, le rapport l'indique au lieu d'une synthèse.

Ce n'est ni un diagnostic ni une prescription : le texte le rappelle.

## Repas

1. **Photos** (facultatives) → le modèle de vision (`OLLAMA_VISION_MODEL`)
   les voit toutes ensemble : il liste les aliments et estime les
   portions en grammes sur l'assiette et, quand il y a plusieurs photos,
   **relève les étiquettes** (boîte, sachet, tableau des valeurs : nom du
   produit, valeurs pour 100 g, poids net). **Votre description fait
   foi** (quantités, cuisson, absence de matière grasse).
2. **Mes aliments** → les aliments choisis dans le formulaire et ceux
   que la description **nomme** sont donnés
   au modèle texte avec leurs **valeurs** et leurs **grammes**, « ils
   font foi ». Les grammes sont **lus par le code** dans la description
   (`meal_quantity`) : grammes écrits à côté (« saumon 100g », « 150 g
   de riz »), sinon un compte (« 2 », « deux », « un demi », « ½ »,
   « 1/2 ») × le poids d'une unité de la fiche, ou × le paquet pour
   « sachet », « boîte », « pot »… ; sinon la **portion habituelle** de
   la fiche (« petite boîte » sans nombre = cette portion), sinon une
   boîte. Chaque fiche est donnée au modèle et affichée **nom · marque ·
   poids** : deux formats d'un produit restent distincts.
   **Nommer un aliment** (`food_match`, par le code, sans accents,
   singulier ou pluriel), dans chaque morceau de la description
   (séparés par des virgules, « et », « + », « avec ») : tout son nom
   ou un de ses autres noms ; ou **un mot de son nom** (« saumon »)
   quand le reste du morceau n'est que des mots à lui (son nom, sa
   marque, son unité « pavé »), un nombre, une taille (« petite »), un
   emballage ou un mot neutre (« nature », « cuit », « grillé »), **et**
   qu'un emballage, son unité, sa marque ou deux mots de son nom le
   confirment. « un pavé de saumon » → « Saumon sauvage rose » (1 pavé
   = 100 g) ; « petite boîte d'aubergines » → « Aubergines cuisinées à
   la provençale ». Mais « filet de poulet » ne nomme pas « Poulet
   basquaise » (« filet » n'est pas à lui), ni « 2 pommes » « Pommes
   rissolées » (rien ne confirme), ni « sachet de riz basmati » un
   autre riz ; un morceau qui va à deux fiches autant n'en nomme
   aucune (la table Ciqual décide) — sauf deux **formats** d'un même
   produit quand le morceau dit lequel : « petite » → le plus petit
   paquet, « grosse / grande » → le plus grand, ou son poids (« 750 g »).
3. **Table Ciqual** → pour les mots de la description et de la photo, le
   code cherche dans la table Ciqual 2025 de l'ANSES (embarquée, hors
   ligne) les références possibles : noms qui commencent par le mot,
   préparées comme le dit le texte (« cuit », « vapeur », « cru »…),
   génériques (« aliment moyen ») d'abord. Cette courte liste (code :
   nom) est donnée au modèle.
4. **Modèle texte** (`OLLAMA_TEXT_MODEL`, décodage glouton, graine
   fixe : la même entrée donne la même sortie) → pour chaque aliment :
   nom, grammes, `food_id` (un de vos aliments) ou `ciqual` (une
   référence **de la liste** : un code hors liste est ignoré), une
   estimation des nutriments. **Pas d'avis à ce stade** : il vient
   après le calcul (étape 7). Les **grammes écrits** dans la
   description (« tomates 240 g », « 150 g de riz ») remplacent ceux du
   modèle, par le code, pour chaque ligne ; chaque ligne dit d'où
   viennent ses grammes (`grams_from` : `écrit`, `compté` — nombre ×
   l'unité ou le paquet de la fiche —, `portion` — votre portion
   habituelle —, `formulaire`, `paquet`, `IA` — estimation du modèle).
   Pour un aliment de « Mes aliments » venu d'Open Food Facts, le
   modèle reçoit aussi ses **informations produit**, qui font foi :
   Nutri-Score, groupe NOVA (1 peu transformé … 4 ultra-transformé),
   additifs, allergènes, repères sel / sucres / gras, part de fruits et
   légumes et le début des ingrédients (400 caractères). Une remarque
   qui met en doute des valeurs connues (« vérifier l'étiquette
   réelle », « vérifier la composition ») est **coupée par le code**
   quand le repas contient un aliment de vos fiches (le reste de la
   remarque est gardé : « Quantité de sodium dans les aubergines »).
5. **Valeurs par le code** : un aliment avec une référence Ciqual prend
   les valeurs de la table pour ses grammes (énergie de la table,
   « < x » compté x/2, « traces » 0, inconnu 0) ; ce que le modèle
   écrit dans `source` est ignoré.
6. **Contrôle** (code, pas d'IA) : un aliment **estimé** est **écarté**, avec sa
   raison, si c'est physiquement impossible — quantité nulle ou > 1,5 kg,
   nutriments plus lourds que l'aliment, sucres > glucides, saturés >
   lipides, sodium impossible. L'**énergie est recalculée** depuis les
   macronutriments (4 kcal/g protéines et glucides, 9 lipides, 2 fibres) :
   les totaux sont cohérents par construction ; un aliment de la table
   ne voit contrôlée que sa quantité. Un aliment de « Mes
   aliments » est ensuite **recalculé par le code** depuis son étiquette
   pour les grammes mangés (ceux du formulaire, sinon ceux estimés,
   sinon le poids du paquet) et marqué « étiquette » : la ligne du
   modèle pour cet aliment (« Saumon » pris dans la table Ciqual,
   « Pavé de saumon grillé ») est remplacée, une **seconde ligne** pour
   lui est retirée (pas de double compte) ; un aliment choisi ou nommé
   que le modèle a oublié est ajouté (s'il a des grammes ou un poids de
   paquet).
7. **Avis, d'après les chiffres exacts** : un second appel au modèle
   texte reçoit la liste calculée par le code (chaque aliment, ses
   grammes et d'où ils viennent, ses nutriments, sa source), le total
   du repas, les informations Open Food Facts, vos maladies déclarées,
   et rend note 0–10, verdict, points positifs, points à surveiller —
   avec la consigne de **recopier** les chiffres, jamais de les
   recalculer. Puis le code **vérifie** : toute quantité citée dans une
   remarque (« 557 mg », « 10.6 g ») doit être une valeur calculée
   (ligne, total, valeur pour 100 g d'une fiche, au même arrondi que
   celui écrit ; sodium aussi en g de sodium ou de sel). Sinon la
   parenthèse qui la contient est coupée (« Assez de sucres (10.6 g
   pour 185 g) » → « Assez de sucres »), ou la remarque est retirée.
   Aucune posologie ni prescription.
8. Les totaux deviennent des relevés `meal` à l'heure du repas, dans les
   mesures nutrition d'Apple Santé ; ce sont des **estimations**
   (±20–30 % typiquement sur les portions), affichées comme telles.

Statuts et délai : comme les documents (en attente → en cours → lu /
échec), 15 minutes maximum ; relancé après un redémarrage du worker.

## Photos (méthode v2)

- Contrôle qualité automatique (luminosité, netteté, résolution) : une
  photo inexploitable n'est jamais notée.
- Notes 0–10 à l'aveugle par angle sur des grilles ancrées (largeur de
  taille, volume du ventre, protrusion, poignées d'amour…).
- Comparaisons appariées avec la photo de référence, J-7, J-30, J-90 : les
  deux images côte à côte, ordre inversé une seconde fois pour annuler le
  biais de position ; une réponse non symétrique est marquée « peu
  fiable ».
- Tendance de fond : médiane par jour, pente robuste (Theil–Sen) sur 90
  jours, seulement avec ≥ 8 jours notés sur ≥ 21 jours, et uniquement avec
  les notes du **modèle de vision actuel**.

## Dépannage

| Symptôme | Cause probable / action |
|----------|------------------------|
| « Lecture IA en cours » ne bouge pas | Le worker attend Ollama. `docker compose logs worker --since 30m`. Au-delà de 30 min la lecture passe en échec avec la raison. |
| `ollama ps` affiche « Stopping… » | Ollama décharge un modèle (fin de requête, changement de modèle, manque de VRAM). Normal entre deux tâches ; si ça se répète pendant une lecture, vérifier la VRAM libre. |
| « délai dépassé » | Document très long ou modèle trop lent : réessayer, ou un modèle plus léger pour `OLLAMA_DOCUMENT_MODEL`. |
| Beaucoup de valeurs rejetées | Le filet fonctionne : les valeurs réellement imprimées sont gardées. Vérifier avec `document_text`. |
| Résumé IA faux | Le résumé est « non vérifié » ; seules les valeurs vérifiées alimentent les courbes. Réanalyser avec `medgemma:27b` en modèle texte. |
| Synthèse vide ou avec beaucoup de phrases retirées | Le modèle n'a pas cité ses faits : relancer, ou utiliser `medgemma:27b`. |
| Aucune IA ne répond | `OLLAMA_URL` injoignable depuis Docker. Tester depuis le worker (c'est lui qui lit documents, repas et photos) : `docker compose exec worker python -c "import httpx,os;print(httpx.get(os.environ['OLLAMA_URL']+'/api/tags').json())"` (doit lister vos modèles) ; pour la lecture d'étiquette, la même commande avec `api` au lieu de `worker`. |
| « Lecture trop longue : réessayer » (Mes aliments › Photo des valeurs) | La lecture d'étiquette tourne **dans l'API**, limitée à **100 s** (`services/food_label.py`), attente comprise. Le verrou « une requête à la fois » est **par processus** (`core/ollama.py`) : l'API ne voit pas le travail du worker, et Ollama peut recevoir les deux demandes ensemble (un repas ou un document en cours de lecture). Réessayer quand le worker a fini, ou remplir la fiche depuis la table Ciqual. |
