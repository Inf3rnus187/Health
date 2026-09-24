# Passer le hub en multi-utilisateur — analyse et plan

Ce document liste **tout** ce qui doit être séparé, protégé ou ajouté pour
que plusieurs personnes utilisent le même hub : web, API, MCP, raccourcis
iPhone, photos, dossiers médicaux, fichiers, tâches IA, mises à jour,
administration. Il vient d'un audit du code (routes, services, modèles,
workers, MCP, page web, déploiement) ; chaque point dit **où** est le
problème, **le risque**, **la correction** et **son état**.

Légende : 🔴 critique (fuite ou modification des données d'un autre),
🟠 élevé, 🟡 moyen, ⚪ confort · ✅ corrigé · ⏳ à faire.

## 1. Principes

1. **Chaque donnée a un propriétaire** (`user_id`) et **chaque requête
   filtre dessus**. Un objet d'un autre répond **404** (jamais 403 : on
   ne révèle pas qu'il existe). Les fichiers sont dans le dossier de leur
   propriétaire (`media/<user_id>/`).
2. **Deux rôles** : `admin` (gère le hub et les comptes) et `user`.
   **L'administrateur ne lit pas les données de santé des autres** : il
   voit des comptes, des volumes et des erreurs, jamais une valeur, une
   photo ou un document. Un partage (aidant, médecin) sera explicite,
   en lecture seule et limité dans le temps.
3. **Tout se fait dans la page web.** Un utilisateur ne tape jamais une
   commande : compte, mot de passe, MFA, jetons, raccourcis, exports,
   suppression du compte. L'administrateur aussi : comptes, invitations,
   mises à jour, IA, journaux, sauvegardes, diagnostic.
4. **Moindre privilège** : une session web n'est pas un jeton, un
   raccourci « +1 café » ne lit rien, un assistant MCP n'administre rien.
   Les actions d'administration exigent la **session interactive** d'un
   admin (jamais un jeton).
5. **Défense en profondeur** : le filtre applicatif d'abord, puis la
   base (Row-Level Security PostgreSQL), des rôles de base séparés, des
   secrets distincts par service.

## 2. Déjà en place

- Presque toutes les tables de santé portent `user_id` et leurs routes
  le filtrent : mesures, échantillons, événements, sommeil, journal,
  repas, **aliments** (nouveau, testé avec un deuxième compte), photos,
  documents médicaux, maladies, traitements, rendez-vous, biologie,
  travail, preuves, traces, absences, rapports, automatisations, jetons.
- Les photos (corps, repas, aliments) et documents vont dans
  `media/<user_id>/`, nettoyés (EXIF/GPS retirés) et chiffrés si le
  chiffrement est activé.
- Les jetons d'API appartiennent à un utilisateur et portent des scopes.
- ✅ **Mises à jour** : l'état et « Installer » (`/system/update`)
  exigent la session d'un `admin` ; les autres voient seulement
  « Nouvelle version installée : recharge la page ».
- ✅ **Catalogue des métriques** : le créer ou le modifier
  (`POST /metrics`, `PATCH /metrics/{key}`) exige le rôle `admin`.
- ✅ **Jetons hors des journaux** : `?token=…` (raccourcis iPhone) est
  écrit `token=***` dans le journal de l'API et celui de nginx.
- ✅ **MCP** : `api_get` / `api_call` n'acceptent que des chemins d'API ;
  une URL complète, `//hôte`, `..` sont refusés avant tout envoi (le
  jeton ne part jamais ailleurs).

## 3. Inventaire par zone

### 3.1 Données partagées entre utilisateurs

| # | Où | Risque | Correction | État |
|---|----|--------|------------|------|
| C1 | `metric_definitions` (le catalogue) est global ; `PATCH/POST /metrics` étaient ouverts à tout jeton `write:metrics` et à toute session | un utilisateur change l'unité, les bornes, l'agrégation ou désactive une métrique **pour tous** ; un libellé piégé entre dans la synthèse IA des autres (injection de consigne) | écriture réservée à l'admin | ✅ |
| H2 | métriques **créées automatiquement** à l'import (type HealthKit inconnu) et métriques personnalisées : globales ; une collision de clé répond 409 | le 409 révèle qu'un autre a créé cette métrique ; ses libellés s'affichent chez tous | colonne `owner_id` (null = catalogue commun) ; clé unique par (propriétaire, clé) ; listes = communes + les miennes ; création auto rattachée à l'importateur | ⏳ |
| H1 | purge biologie `_drop_empty` : supprime une définition `bio.*` vide **pour moi** | la suppression en cascade efface les échantillons `bio.*` **des autres** | ne supprimer une définition que si **plus personne** n'a de donnée (ou jamais : la masquer pour moi) ; test à deux comptes | ⏳ |
| H3 | exports Apple Health déposés dans `exports/imports/` | jamais supprimés, pas rangés par utilisateur, en clair | dossier `exports/imports/<user_id>/`, suppression après import (ou 24 h), chiffrement au repos | ⏳ |

### 3.2 Références non vérifiées (un identifiant d'un autre)

| # | Où | Risque | Correction | État |
|---|----|--------|------------|------|
| M1 | `POST /measurements` avec `event_id` | rattacher ma mesure à l'événement d'un autre | vérifier que l'événement est à moi (404 sinon) | ⏳ |
| M2 | preuves avec `absence_id` | idem pour une absence | idem | ⏳ |
| — | repas avec `foods` | idem pour un aliment | vérifié : 404 | ✅ |

Règle générale à tester : **tout identifiant reçu dans un corps ou un
formulaire** (`*_id`) est rechargé avec `user_id` avant usage.

### 3.3 Traces et journaux

| # | Où | Risque | Correction | État |
|---|----|--------|------------|------|
| C | `?token=` dans les URL (raccourcis) → journaux gunicorn/uvicorn et nginx | vol d'un jeton en lisant un journal | filtrés (`token=***`) | ✅ |
| M3 | journal d'audit | garde des valeurs de santé après l'effacement du compte | n'y écrire que l'action, l'entité et l'id ; purge à la suppression du compte | ⏳ |
| — | journaux applicatifs | des valeurs de santé ou des textes de repas peuvent y passer | relecture des `log.*` : ids et compteurs seulement | ⏳ |

### 3.4 Authentification et sessions

| # | Point | Correction | État |
|---|-------|------------|------|
| 🟠 | pas de limite de tentatives ni de blocage à la connexion | limite par IP et par compte (ex. 5/min, blocage progressif), journalisée | ⏳ |
| 🟡 | le temps de réponse révèle si un e-mail existe | hacher un mot de passe factice quand le compte n'existe pas | ⏳ |
| 🟡 | e-mail sensible à la casse | e-mail normalisé en minuscules (migration + index unique) | ⏳ |
| 🟠 | le jeton d'accès (JWT) reste valable après la déconnexion (`sid` non vérifié) | vérifier la session à chaque requête (cache court) ; la déconnexion la révoque | ⏳ |
| 🟠 | le renouvellement ne revérifie pas `is_active` | un compte désactivé perd tout à la minute | ⏳ |
| 🟠 | MFA : un nouveau secret remplace l'ancien sans le code actuel ; pas de codes de secours ; secret en clair | exiger le code actuel (ou le mot de passe) ; 10 codes de secours hachés ; secret chiffré | ⏳ |
| 🔴 | MFA activée = web inutilisable (le formulaire n'a pas de champ code) | champ code à la connexion, écran d'activation avec QR | ⏳ |
| 🟠 | `ADMIN_PASSWORD` d'exemple accepté (`change-me-please` dans le code, `change-me-admin-password` dans `.env.example`) ; un `SECRET_KEY` d'exemple passe la validation | refuser de démarrer avec ces valeurs ; premier admin créé par l'assistant d'installation web (mot de passe choisi à l'écran) | ⏳ |
| ⚪ | pas de changement de mot de passe, de fuseau, de liste des sessions | page **Mon compte** (§5) | ⏳ |

### 3.5 Jetons d'API, scopes et raccourcis iPhone

Aujourd'hui : `ingest:watch`, `ingest:ppc`, `ingest:photo`,
`write:measurements`, `write:metrics`, `read:all`, `hub:full`. Problèmes :

- **toute session web passe tous les contrôles de scope** : normal pour
  le propriétaire, mais rien ne distingue une action d'admin ;
- `write:measurements` est large (compteurs, repas, sommeil, travail…)
  alors qu'un raccourci n'a besoin que d'une chose ;
- `read:all` est incohérent (il lance des rapports mais ne lit pas le
  dossier) ;
- `hub:full` (MCP) donne tout, y compris `api_call` vers n'importe
  quelle route ;
- jetons **sans expiration**, sans « dernière utilisation » visible.

**Modèle cible** — un scope = un usage, jamais d'administration par
jeton :

| Scope | Permet | Pour |
|-------|--------|------|
| `counter:add` | `POST /sync/tally` (eau, café, cigarette, pipi, pointage) | raccourcis « +1 » |
| `meal:add` | `POST /meals` (photos, aliments) | raccourci repas |
| `photo:ingest` | `POST /ingest/photo` | raccourci photo corps |
| `hae:ingest` | `/sync/auto-export` | Health Auto Export |
| `watch:ingest`, `ppc:ingest` | montre, PPC | appareils |
| `import:upload` | imports de fichiers | scripts d'import |
| `data:read` | lecture de **mes** données (dossier compris) | tableaux externes |
| `data:write` | écriture de mes données | intégrations |
| `mcp:read` | outils MCP de lecture | assistant en lecture |
| `mcp:write` | lecture + écriture de mes données par MCP (sans `api_call` libre vers les routes sensibles) | assistant complet |
| `catalog:write` | catalogue commun (**admin seulement**) | admin |
| `admin:*` | — aucun jeton : session admin interactive uniquement | — |

Et :

- **expiration** au choix (30 j, 90 j, 1 an, jamais pour un appareil),
  « dernière utilisation » et IP visibles, révocation en un clic ;
- les raccourcis envoient le jeton **en en-tête** `Authorization` quand
  l'action iPhone le permet (« Obtenir le contenu de l'URL » › En-têtes) ;
  `?token=` reste accepté pour les anciens raccourcis (masqué des
  journaux) ;
- le **générateur de raccourcis** crée un jeton au scope exact du
  raccourci choisi, au nom de l'utilisateur connecté ;
- migration : `hub:full` → `mcp:write`, `write:measurements` → les
  scopes des raccourcis existants (liste proposée à l'utilisateur, il
  coche), `read:all` → `data:read`.

### 3.6 MCP

| # | Point | Correction | État |
|---|-------|------------|------|
| 🔴 | `api_get`/`api_call` acceptaient une URL complète : le jeton de l'appelant partait vers l'hôte donné | chemins d'API seulement | ✅ |
| 🟠 | le conteneur MCP reçoit tout le `.env` (dont `SECRET_KEY`, mots de passe) | un `env` minimal : `API_BASE_URL`, `MCP_TRANSPORT` | ⏳ |
| 🟠 | `hub:full` trop large ; la porte accepte aussi un jeton de connexion | `mcp:read` / `mcp:write` seulement ; refuser les JWT de session | ⏳ |
| 🟡 | sessions SSE non liées au jeton qui les a ouvertes | lier l'id de session au jeton ; refuser un autre jeton | ⏳ |
| 🟡 | `api_call` peut viser des routes sensibles | liste de routes interdites (`/tokens`, `/auth`, `/mfa`, `/account`, `/system`, `/admin`), déjà refusées côté API pour un jeton | ⏳ |

### 3.7 Fichiers, rapports, exports

| # | Point | Correction | État |
|---|-------|------------|------|
| 🟠 | rapports PDF / exports en clair et gardés sans limite | chiffrés comme les photos, durée de conservation (ex. 30 j), suppression avec le compte | ⏳ |
| 🟡 | clé de chiffrement unique et facultative | obligatoire dès le 2e compte ; à terme une clé par utilisateur (enveloppe) | ⏳ |
| 🟠 | limites d'envoi incomplètes (archive zip : bombe possible) | taille décompressée maximale, nombre d'entrées, quota par utilisateur | ⏳ |
| 🟡 | quota disque par utilisateur absent | quota + affichage dans Mon compte et Admin | ⏳ |

### 3.8 Tâches IA (worker, Ollama)

- une seule file et un seul modèle chargé à la fois : un utilisateur qui
  lance 200 lectures de documents bloque les repas des autres, et le
  délai maximum compte l'attente → échecs en chaîne ;
- correction : **équité par utilisateur** (tourniquet, N tâches en cours
  max par personne), délai compté à partir du début réel, priorités
  (repas et étiquettes avant les relectures de masse), file visible
  (« 3 lectures avant la tienne ») ; l'admin voit la file et peut la
  purger.

### 3.9 Page web

| # | Point | Correction | État |
|---|-------|------------|------|
| 🔴 | le cache des requêtes (react-query) n'est pas vidé à la déconnexion ni au changement de compte | `queryClient.clear()` à la connexion et à la déconnexion | ⏳ |
| 🟠 | le jeton de renouvellement est dans `localStorage`, partagé entre onglets : un onglet peut changer de compte en silence | cookie `HttpOnly; Secure; SameSite=Strict` pour le renouvellement ; au changement d'utilisateur, les autres onglets rechargent | ⏳ |
| 🟡 | préférences `phoenix.view.*` communes à tous les comptes du navigateur (recherche dans les preuves, heures de contrat…) | préfixées par l'id utilisateur ; aucune donnée de santé dans le navigateur | ⏳ |
| ⚪ | pas de page Mon compte, pas de page Admin | §5 et §6 | ⏳ |

### 3.10 Hôte, déploiement, mises à jour

| # | Point | Correction | État |
|---|-------|------------|------|
| 🟡 | `run/` est en `1777` : tout compte local de la machine peut demander une mise à jour | groupe dédié (`phoenix`), `0770` | ⏳ |
| 🟡 | base : un seul rôle PostgreSQL propriétaire de tout | rôle applicatif sans DDL, rôle de migration séparé ; RLS par `user_id` (`SET app.user_id` par transaction) | ⏳ |
| 🟡 | Redis sans mot de passe | `requirepass`, réseau interne seulement | ⏳ |
| ✅ | « Installer » réservé à l'admin | fait | ✅ |

## 4. Rôles et accès — la matrice

| Qui / par où | Ses données | Données des autres | Comptes, MAJ, IA, journaux |
|--------------|-------------|--------------------|-----------------------------|
| Utilisateur, page web | tout | jamais (404) | non |
| Admin, page web | tout (les siennes) | **jamais les valeurs** : comptes, volumes, erreurs | oui (session interactive, MFA exigée) |
| Jeton (raccourci, appareil) | son scope seulement | jamais | jamais |
| MCP (jeton `mcp:*`) | lecture / écriture selon le scope | jamais | jamais |

## 5. Page « Mon compte » (chaque utilisateur)

- **Profil** : nom affiché, e-mail (changement confirmé par lien), fuseau
  horaire, unités.
- **Sécurité** : changer le mot de passe (l'actuel exigé), **MFA** (QR,
  code de vérification, 10 codes de secours, désactivation avec un
  code), **sessions** ouvertes (appareil, IP, dernière activité, « Se
  déconnecter partout »).
- **Jetons et raccourcis** : créer un jeton depuis un **modèle** (« +1
  café », « Repas », « Photo corps », « Health Auto Export », « Assistant
  MCP lecture », « Assistant MCP complet ») → scope exact, expiration,
  jeton affiché une seule fois ; télécharger le raccourci iPhone déjà
  rempli ; liste avec dernière utilisation et « Révoquer ».
- **Mes données** : volume stocké, export complet (JSON/CSV/FHIR +
  fichiers), **supprimer mon compte** (export proposé, e-mail retapé,
  suppression des données, fichiers, jetons, lignes d'audit nominatives).

## 6. Page « Administration » (`/admin`, rôle admin, session + MFA)

| Onglet | Contenu |
|--------|---------|
| **Utilisateurs** | liste (e-mail, nom, rôle, actif, MFA, créé le, dernière connexion, stockage, nombre d'éléments) ; **inviter** (lien à usage unique valable 72 h, l'invité choisit son mot de passe) ; **créer** (mot de passe provisoire, changement forcé) ; désactiver / réactiver ; lien de réinitialisation du mot de passe ; **réinitialiser la MFA** ; changer le rôle (il reste toujours au moins un admin) ; révoquer toutes ses sessions et tous ses jetons ; supprimer (e-mail retapé) |
| **Statistiques** | comptes actifs 7 / 30 j, connexions, stockage par compte, lignes par compte et par source, tâches IA par compte (nombre, durée, échecs), dernière synchronisation par source — **jamais une valeur de santé** |
| **Diagnostic** | par compte : tâches bloquées (relancer), imports en échec (message), recalcul des valeurs du jour, synchronisation qui n'arrive plus ; « se mettre à la place » **interdit** |
| **Mises à jour** | la bannière actuelle + l'historique (version, date, résultat, journal) ; installation automatique on/off |
| **IA** | Ollama joignable ?, modèles installés, modèle par tâche, file d'attente (par compte), purge, test d'un modèle |
| **Journaux et audit** | erreurs récentes, échecs de connexion, actions d'admin (qui, quoi, quand) ; filtrables ; sans données de santé |
| **Stockage et sauvegardes** | disque utilisé / libre, dernière sauvegarde, « Sauvegarder maintenant », rétention, instructions de restauration |
| **Intégrations** | clé de carte, SMTP (invitations, réinitialisations), URL publique |
| **Catalogue** | métriques communes : libellé, unité, bornes, active, fusion d'alias |

Routes à créer (toutes `AdminDep` sauf mention) : `GET/POST /admin/users`,
`PATCH/DELETE /admin/users/{id}`, `POST /admin/users/{id}/invite`,
`/reset-password`, `/reset-mfa`, `/revoke`, `GET /admin/stats`,
`GET /admin/users/{id}/diagnostic`, `POST /admin/jobs/{id}/retry`,
`GET /admin/audit`, `GET /admin/logs`, `GET/PUT /admin/settings`,
`GET/POST /admin/backups`, `GET /admin/ai`, `POST /auth/invitations/{code}`
(public : accepter une invitation), `PUT /account/password`,
`PATCH /account`, `GET/DELETE /account/sessions[/{id}]`,
`POST /account/mfa/recovery-codes`, `DELETE /account` (session).

## 7. Tests d'isolation (le filet)

- **Un test généré depuis OpenAPI** : pour chaque route `GET` qui prend
  un identifiant, un objet créé par A et demandé par B répond 404 ; pour
  chaque liste, B ne voit rien de A. Toute nouvelle route y passe
  automatiquement.
- Tests à deux comptes pour chaque correction ci-dessus (H1, H2, M1, M2,
  cache web, onglets).
- Tests de scope : chaque modèle de jeton appelle toutes les routes ; la
  matrice attendue est un fichier relu.
- Tests MCP : un jeton `mcp:read` ne peut rien écrire ; aucun outil
  n'atteint une route d'admin.

## 8. Plan par étapes

0. **Fait** : mises à jour réservées à l'admin, bandeau « recharge » pour
   les autres, jetons masqués dans les journaux, MCP limité aux chemins
   d'API, catalogue réservé à l'admin, aliments par utilisateur.
1. **Isolation (avant tout deuxième compte réel)** : H1, H2, H3, M1, M2,
   M3 ; cache web vidé, préférences par compte ; session vérifiée à
   chaque requête, `is_active` au renouvellement ; test d'isolation
   généré.
2. **Comptes dans la page web** : Mon compte (mot de passe, MFA avec
   champ code à la connexion, sessions), page Admin › Utilisateurs
   (inviter, créer, désactiver, réinitialiser), limite des tentatives,
   premier admin créé à l'installation.
3. **Scopes fins** : nouveaux scopes, modèles de jetons, expiration,
   raccourcis générés par utilisateur, migration des jetons existants,
   MCP `mcp:read` / `mcp:write`, `env` MCP minimal.
4. **Durcissement** : RLS PostgreSQL, rôles de base, mot de passe Redis,
   `run/` en groupe, chiffrement obligatoire, rapports chiffrés et
   purgés, quotas et limites d'envoi, équité de la file IA.
5. **Exploitation** : Admin › Statistiques, Diagnostic, IA, Journaux,
   Sauvegardes, Intégrations.

Chaque étape se livre avec ses tests (dont ceux à deux comptes), sa
documentation et une entrée du changelog ; l'étape 1 est un prérequis
bloquant : **pas de deuxième compte réel avant qu'elle soit finie**.
