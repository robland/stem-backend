# StemLearningApp — Frontend (Web React + Mobile)

> **Destinataires : agents Claude (et développeurs) qui implémentent le web et le mobile.**
> Lisez ce fichier **en entier** avant toute modification. Il fait foi sur le périmètre, l'UX, les technos et l'état d'avancement.
> Le backend et **le contrat de contenu (schéma d'activités)** sont décrits dans [`../README.md`](../README.md) — §1 (contexte), §6 (schéma d'activités) et §7 (API) sont **à connaître impérativement**.

---

## 1. Contexte produit (résumé)

- Application **gratuite**, **en français uniquement**, pour **collégiens et lycéens** de la **République du Congo** (préparation **BEPC** et **BAC**).
- L'élève **photographie son exercice** ; l'app le fait **raisonner étape par étape** avec des interactions propres à chaque matière, sans jamais donner la solution d'emblée. Il peut ensuite **lancer un défi** aux autres élèves avec cet exercice.
- Matières (livrées par vagues) : Maths, Physique-Chimie, SVT, Anglais, Français, Histoire-Géographie.
- **Hors-ligne obligatoire** : un parcours déjà généré se refait sans connexion.
- **Données personnelles** : uniquement le numéro de téléphone (connexion). L'élève est affiché par un **pseudo**. Pas de nom, photo de profil, e-mail, localisation.
- Pas d'espace parents ni enseignants.

### Contraintes terrain (à garder en tête à chaque écran)
- Réseau **lent et instable**, data chère → bundles légers, images compressées **avant** envoi (~1600 px max, JPEG qualité ~0.8), aucune ressource lourde chargée sans besoin, offline-first.
- **Android d'entrée de gamme** prioritaire (peu de RAM, petits écrans) → animations sobres (60 fps sur appareil modeste), listes virtualisées, pas de dépendances géantes.
- Utilisation typique : **devant son cahier, téléphone en main**.

---

## 2. Principes UX

1. **Mobile d'abord**, même pour le web.
2. **Un écran = une idée** : parcours en cartes successives, pas de pavés de texte.
3. **Agir avant de lire** : l'élève tente, puis on explique.
4. **L'erreur est normale** : feedback immédiat, bienveillant, **ciblé** sur l'erreur commise (`common_mistakes`), jamais un simple « Faux ».
5. **Indices toujours accessibles** (bouton 💡, 3 niveaux, coût en points affiché).
6. **Ton adapté au niveau** (collège plus imagé, lycée plus rigoureux) — vient du contenu, l'UI reste neutre.
7. **Accessibilité** : police adaptée à la dyslexie en option, lecture audio des énoncés (synthèse vocale de l'appareil), mode sombre, cibles tactiles ≥ 44 px, contrastes AA.
8. **Feedback de chargement pédagogique** : l'analyse prend 20–60 s → progression en direct (SSE), messages explicites, parcours affiché dès qu'il est prêt (l'événement `ready` contient le contenu).

### Navigation (5 onglets)

```
[ Accueil ]  [ Défis ]  [ 📷 Scanner ]  [ Progrès ]  [ Profil ]
```
Le bouton **Scanner** est central et mis en avant (action principale).

### Parcours clés

| Parcours | Écrans |
|---|---|
| **Onboarding** (< 1 min) | Téléphone + mot de passe + pseudo → niveau (6e→Tle) et série → matières → objectif (devoirs / BEPC / BAC) → exercice de démonstration |
| **Accueil** | « Continuer » (parcours en cours) · « Révision du jour » · « Défis reçus » · progression de la semaine (série de jours, XP) |
| **Scanner** | Photo → recadrage → envoi (compressé) → détection des exercices (« 3 exercices trouvés, lequel ? ») → **vérification/correction de l'énoncé** (aperçu LaTeX en direct) → matière/chapitre (modifiable) → attente animée → parcours |
| **Résolution** | Barre de progression des étapes en haut · carte Intuition · cartes Rappel · une activité par écran · 💡 Indice · feedback immédiat animé · Bilan (réussites, erreurs, notion clé) → « Refaire » / « Lancer un défi » (« Exercice similaire » abandonné, décision du 2026-11-07) |
| **Défis** (V2) | Catalogue filtré matière/chapitre/niveau · rejoindre par code · créer (public/privé, chrono, indices on/off) · classement entre amis / par niveau (jamais global ouvert) |
| **Progrès** | Maîtrise par chapitre (non acquis / en cours / maîtrisé) · points faibles · révision espacée |
| **Profil** | Pseudo, niveau/série, préférences d'accessibilité, gestion des contenus hors-ligne (espace utilisé, suppression), déconnexion |

> Avant d'implémenter un écran majeur, produire une **maquette** et la faire valider par le porteur du projet.

---

## 3. Technologies

### Monorepo
**pnpm workspaces + Turborepo**, TypeScript strict partout.

```
frontend/
├── apps/
│   ├── web/              React + Vite (V1)
│   └── mobile/           React Native + Expo (V3)
├── packages/
│   ├── api-client/       client TS **généré** depuis l'OpenAPI du backend (openapi-typescript / orval) + hooks TanStack Query
│   ├── content-schema/   types + validation (Zod) du schéma d'activités (miroir du §6 backend)
│   ├── grading/          correction côté client pour le hors-ligne (exact, normalized_text, numeric, symbolic, chem_balance)
│   ├── activities/       composants d'activités (un renderer par `type`)
│   ├── offline/          stockage local, file de synchronisation
│   └── ui/               design system (tokens, composants de base)
└── README.md
```

### Web (`apps/web`)
- **React 18 + TypeScript + Vite**, React Router, **TanStack Query**.
- UI : **Tailwind CSS + shadcn/ui** (Radix, accessible), **Framer Motion** (animations, avec `prefers-reduced-motion`).
- Formulaires : React Hook Form + Zod.
- Hors-ligne : **PWA** (Workbox) + IndexedDB (via Dexie) + persistance du cache TanStack Query.

### Mobile (`apps/mobile`) — React Native + **Expo**
- Expo Router, EAS Build/Update, `expo-camera` / scan de documents, `expo-image-manipulator` (recadrage, compression), `expo-secure-store` (refresh token), `expo-sqlite` (hors-ligne), `expo-notifications` (rappels, défis), `expo-speech` (lecture audio).
- Les briques DOM (MathLive, JSXGraph, KaTeX) sont réutilisées via les **DOM components d'Expo** (`"use dom"`) ou une WebView ; ne réécrire en natif (react-native-svg / Skia) que si les performances l'exigent.
- **Android prioritaire** ; tester sur un appareil/émulateur bas de gamme.

### Briques par activité

| Besoin | Librairie |
|---|---|
| Affichage maths + chimie | **KaTeX** + extension **mhchem** (`\ce{}`) |
| Saisie de formules (`formula_input`) | **MathLive** (clavier mathématique virtuel, `\placeholder{}`) |
| Équivalence symbolique hors-ligne | **CortexJS Compute Engine** (compagnon de MathLive) |
| Repères, courbes animées, curseurs (`graph_points`, `graph_parameters`) | **JSXGraph** (ou Mafs si suffisant — choisir et noter ici) |
| Tableau de variations | composant maison (SVG) |
| Équilibrage chimique (`chem_balance`) | composant maison : stepper de coefficients + compteur d'atomes en direct |
| Molécules (si besoin) | **Ketcher** (chargé à la demande uniquement) |
| Glisser-déposer (`matching`, `ordering`, `label_diagram`, `timeline`) | **dnd-kit** (web) / react-native-gesture-handler + reanimated (mobile) |
| Cartes (`map_locate`) | cartes **SVG** légères embarquées (pas de tuiles réseau) |

> Toute librairie lourde (Ketcher, JSXGraph…) est **chargée à la demande** (code-splitting), jamais dans le bundle initial.

---

## 4. Règles de rendu du contenu

- Le contenu arrive au format du **schéma d'activités** (backend §6). Le valider avec `packages/content-schema` (Zod) ; une étape invalide affiche un état d'erreur propre et un bouton « Signaler », jamais un crash.
- Tout texte est du **texte riche** : texte + `$...$` / `$$...$$` (KaTeX) + `\ce{...}`. **Ne jamais interpréter de HTML** (`dangerouslySetInnerHTML` interdit sur du contenu généré).
- **Un renderer par `type` d'activité** dans `packages/activities` (`definitions` dans `registry.tsx`), interface commune (`types.ts`) :
  ```ts
  type RendererProps<A, R> = {
    activity: A;                       // payload sans réponse (mode en ligne)
    value: R | undefined;              // réponse contrôlée par le lecteur (bouton « Vérifier » dans sa barre)
    onChange: (value: R) => void;
    disabled?: boolean;
    details?: Record<string, unknown> | null; // `details` de l'API : marque les éléments justes / faux
    seed: string;                      // id de l'étape : mélange stable (classement, appariement)
  };
  type ActivityDefinition<A, R> = {
    Renderer; isComplete(activity, value): boolean; initial?(activity, seed): R;
    serialize?(value): unknown;        // réponse au format backend README §5.1
    ownsPrompt?: boolean;              // consigne rendue par le renderer (formule à compléter)
  };
  ```
  (Remplace l'interface `onSubmit` initiale, 2026-11-07 : la réponse doit rester affichée et corrigeable après une erreur.)
- Un `type` inconnu (version de schéma plus récente) → écran « Mets l'application à jour » pour cette étape.

| `type` | Version | Renderer |
|---|---|---|
| `mcq`, `true_false`, `short_answer`, `fill_blanks`, `matching`, `ordering` | V1 | communs |
| `formula_input`, `graph_points`, `graph_parameters`, `variation_table` | V1 | Maths |
| `chem_balance`, `chem_formula`, `unit_conversion` | V1 | Physique-Chimie |
| `conjugation`, `free_text` | V2 | Français / Anglais |
| `label_diagram`, `timeline`, `map_locate`, `flashcards` | V3 | SVT / Histoire-Géo / révision |

---

## 5. Hors-ligne

- Quand un parcours de l'élève est ouvert (ou sur action « Télécharger »), récupérer `GET /api/exercises/{id}/offline` (contenu **avec réponses**, propriétaire uniquement) et le stocker localement (IndexedDB web / SQLite mobile).
- En hors-ligne : correction locale via `packages/grading` (tous les modes **sauf** `llm_rubric`) ; les activités `free_text` sont mises en attente « sera corrigé à la reconnexion ».
- Chaque réponse reçoit un `client_uuid` (UUID v4) et entre dans une **file de synchronisation** ; à la reconnexion, `POST /api/sync` (idempotent). Le serveur fait foi : en cas d'écart, afficher le résultat serveur.
- Une tentative hors-ligne reçoit son `id` (UUID v4) côté client ; chaque réponse transmet `answered_at` et `hints_used` (indices consultés sur l'étape). Reproduire localement les règles de progression et de score du backend README §5.2 (étapes dans l'ordre, 3 erreurs max, −20 par indice et par erreur).
- **Défis : en ligne uniquement** (correction serveur, pas de réponses en local).
- Indicateur réseau discret + nombre d'éléments en attente de synchro.

---

## 6. API

- Utiliser **uniquement** `packages/api-client`, régénéré depuis `/api/schema/` du backend (`pnpm api:generate`). Pas d'appels `fetch` écrits à la main.
- Auth : access token JWT en mémoire ; refresh en cookie httpOnly (web) / `expo-secure-store` (mobile, refresh envoyé dans le body) ; rafraîchissement automatique sur 401.
- Correction hors-ligne (`packages/grading`) : reproduire **exactement** les règles du backend README §5.1 (formats de réponse, normalisation du texte et des nombres, syntaxe des expressions, forme des expressions `answer.form`, formules chimiques) ; des cas de test partagés seront exportés depuis `grading/tests`.
- Progression : SSE `GET /api/uploads/{id}/events` (extraction) et `GET /api/exercises/{id}/events` (génération), cf. backend README §7. Client SSE basé sur `fetch` (ex. `@microsoft/fetch-event-source`) pour envoyer l'en-tête `Authorization` — l'`EventSource` natif ne le permet pas, et jamais de jeton dans l'URL. Fermer le flux sur un statut final ; sur une fermeture du serveur, se reconnecter (l'état courant est renvoyé). Fallback polling `GET /api/uploads/{id}` / `GET /api/exercises/{id}` toutes les 3 s si SSE indisponible.
- Uploads : l'API n'expose jamais le fichier envoyé → **garder la photo locale** pour l'afficher à côté de l'énoncé pendant la correction. Réenvoyer le même fichier est sans risque (réponse `200`, même upload). Sur `429`, afficher le quota atteint et l'heure de `Retry-After`. Compresser avant envoi (≤ 10 Mo, côté long ~2048 px suffit).
- Si un endpoint nécessaire n'existe pas encore : **ne pas l'inventer côté front**, le signaler et l'ajouter à l'état d'avancement du backend.

---

## 7. État d'avancement

> **Agents : mettez à jour cette section à chaque tâche terminée** (cocher, date `AAAA-MM-JJ`, une ligne de note si utile).
> Dernière mise à jour : 2026-11-07 — Phase 1 web (branche `feature/backend-phase1`) : monorepo, design system, client API, schéma de contenu, auth + onboarding, scanner, lecteur de parcours et renderers des 13 types V1 (en ligne), écran Progrès ; 174 tests verts. Reste : hors-ligne (PWA, IndexedDB, synchro), accueil définitif, Playwright.

### Lancer le frontend

Node tourne dans Docker (aucune installation sur la machine) ; le service `frontend` du `docker-compose.yml` racine monte le dépôt et relaie `/api` vers `web`.

```bash
docker compose up frontend                              # http://localhost:5173 (installe les dépendances au démarrage)
docker compose run --rm --no-deps frontend pnpm test    # typecheck : pnpm typecheck ; lint : pnpm lint ; build : pnpm build
docker compose run --rm --no-deps frontend pnpm api:generate     # après un changement d'API (backend démarré)
docker compose run --rm --no-deps frontend pnpm schema:generate  # après `manage.py export_content_schema`
```

Après un changement de dépendances : `docker compose run --rm --no-deps frontend pnpm install` (le `pnpm-lock.yaml` est versionné).

### Décisions (2026-11-07)
- **Node dans Docker** (choix du porteur du projet) : image `frontend/Dockerfile` (Node 22, pnpm via corepack, utilisateur `node`).
- **Matières et objectif** de l'onboarding : **préférences locales** à l'appareil (`apps/web/src/lib/preferences.ts`), l'API ne les stocke pas.
- **Séries** : l'API accepte un texte libre (≤ 10 caractères) sans liste ; liste centralisée `SERIES` (`A`, `C`, `D`) dans `apps/web/src/strings/fr.ts`, **à confirmer**.
- **Polices système** (aucun téléchargement) ; OpenDyslexic chargée seulement si l'option est activée.
- **Client API** : `openapi-typescript` (types) + `openapi-fetch` (client typé, ~6 kB) ; jeton d'accès en mémoire, refresh par cookie httpOnly, relance automatique sur 401 (un seul refresh à la fois).
- **Schéma de contenu** : générateur maison (`packages/content-schema/scripts/generate.mjs`) plutôt que json-schema-to-zod (qui ne résout pas les `$ref`) : un schéma Zod nommé par `$defs`, unions discriminées par `type`, variantes publiques dérivées. `pnpm test` échoue si le fichier généré n'est pas à jour.
- Nom de l'application : provisoire (`APP_NAME = "StemLearning"`), **à décider**.
- **Saisie des formules : deux variantes développées pour être comparées** (décision du porteur du projet, à prendre après essai) — réglage « Saisie des formules » du Profil :
  - **Simple** (par défaut) : champ texte + touches (x, x², xⁿ, √, a/b, parenthèses, π), expression rendue en direct dans la case `\placeholder{}` de la consigne ; ≈ 8 kB gzip.
  - **MathLive** (`mathlive` 0.111.1, ≈ 229 kB gzip chargés au premier usage) : clavier mathématique ; valeur lue en ASCIIMath puis contrôlée par le même analyseur.
  - Les deux envoient l'expression ASCII du contrat (§5.1). Critères d'évaluation proposés : rapidité de saisie sur téléphone d'entrée de gamme, erreurs de saisie, poids, compréhension par les élèves.
- **Écrans lourds chargés à la demande** (scanner, lecteur) : bundle initial ≈ 133 kB gzip.

### Phase 1 — V1 Web (Maths + Physique-Chimie)
- [x] Initialiser le monorepo (pnpm, Turborepo, TS strict, ESLint, Prettier, Vitest) — 2026-11-07.
- [x] `packages/ui` : tokens (clair/sombre, contrastes AA, cibles ≥ 44 px), Button, Input, Select, Field, ChoiceGroup, Card, Alert, ProgressBar, Spinner — 2026-11-07.
- [x] `packages/api-client` : types générés depuis l'OpenAPI + hooks TanStack Query (auth, me, référentiel, progrès) + refresh automatique — 2026-11-07. Hooks uploads / parcours / tentatives et client SSE à ajouter avec leurs écrans.
- [x] `packages/content-schema` : Zod généré depuis le JSON Schema `1.1`, variantes publiques (`ExerciseContentPublic`), `parseActivity` (type inconnu / invalide sans crash), fixtures miroir de `llm/tests/factories.py` — 2026-11-07.
- [ ] Maquettes validées : onboarding, accueil, scanner, résolution, bilan, progrès.
- [x] Auth + onboarding (téléphone, pseudo, mot de passe → classe/série → matières → objectif), session restaurée au chargement, profil (pseudo, classe, série, thème, police dyslexie, déconnexion) — 2026-11-07. Navigation 5 onglets responsive (barre en bas sur mobile, latérale ≥ `lg`). Accueil minimal en attendant sa maquette.
- [x] Scanner web — 2026-11-07 :
  - photo (caméra arrière via `capture`) ou import photo/PDF ; recadrage au doigt ou au clavier, rotation, réduction à 1 600 px de côté long et JPEG 0,8 (EXIF supprimés par le réencodage) ; PDF envoyé tel quel (≤ 10 Mo) ;
  - suivi de la lecture puis de la génération en direct (`followEvents`, SSE par fetch avec Bearer, reconnexion, repli en polling 3 s) ; le flux ne démarre qu'après le premier GET (sinon une réponse GET plus ancienne écrasait un événement reçu) ;
  - onglets par exercice trouvé, énoncé modifiable avec aperçu KaTeX en direct, matière / classe / chapitre (chapitre lu sur la feuille affiché), écarter, puis correction → validation → génération → écran de préparation (relance si échec, quota avec heure de reprise) ;
  - photo gardée **en mémoire** à côté de l'énoncé (perdue au rechargement : persistance avec `packages/offline`).
- [x] `packages/activities` : `RichText` (texte + `$…$` / `$$…$$` + `\ce{}`), KaTeX et mhchem chargés à la demande (≈ 86 kB gzip hors bundle initial), jamais de HTML interprété — 2026-11-07.
- [x] Lecteur de parcours (`/parcours/:id`, plein écran sans onglets) — 2026-11-07 : intro (énoncé, lecture audio) → intuition → rappels → une étape par écran → bilan (score, étapes, notion clé, « Refaire »). Tentative en ligne : `id` généré par le client et mémorisé sur l'appareil (reprise « où j'en étais », ou `?tentative=` depuis la révision du jour) ; indices demandés un par un à l'API (le 1ᵉʳ aussi, sinon il n'est pas décompté), coût affiché ; réponse renvoyée avec le même `client_uuid` après une coupure ; après une erreur, feedback ciblé, essais restants, réponse à modifier avant de renvoyer ; correction rédigée à la clôture. « Exercice similaire » et « Lancer un défi » désactivés (pas d'endpoint).
- [x] Renderers V1 des 13 types — 2026-11-07 :
  - communs : `mcq`, `true_false`, `short_answer` (clavier décimal en numérique), `fill_blanks` (trous dans le texte), `matching` (**toucher-toucher** au lieu du glisser-déposer : petits écrans, clavier), `ordering` (**flèches** monter/descendre, ordre de départ mélangé de façon stable) ;
  - Maths : `formula_input` (deux saisies **en évaluation**, cf. ci-dessous), `graph_points` & `graph_parameters` (**SVG maison** plutôt que JSXGraph : points à glisser doublés de champs numériques, curseurs et courbe redessinée), `variation_table` (signe et flèche par intervalle) ;
  - PC : `chem_balance` (coefficients + compteur d'atomes et de charges en direct), `chem_formula` (aperçu `\ce{}`), `unit_conversion` (texte envoyé tel quel, lu par l'API).
  - Analyseurs partagés dans `packages/activities/src/math/` : expressions (syntaxe §5.1, aperçu LaTeX, évaluation pour les courbes) et formules chimiques (atomes, charges, hydrates) — base de la future correction hors-ligne.
- [ ] `packages/grading` (hors-ligne) + `packages/offline` (IndexedDB, file de synchro) + PWA.
- [x] Écran Progrès — 2026-11-07 : chiffres clés (parcours terminés, score moyen, série de jours), révision du jour (partagée avec l'accueil, « à terminer » rouvre la tentative), score moyen par matière, points faibles (3 chapitres non maîtrisés les plus bas), maîtrise par chapitre avec filtre par matière et prochaine révision (« demain », « dans 3 jours », fuseau de Brazzaville), « Mes parcours » paginés par curseur. Jauges `Meter` d'une seule teinte avec la valeur écrite ; états de maîtrise avec icône + libellé (jamais la couleur seule). Tant que les chapitres du programme ne sont pas saisis côté backend, la maîtrise par chapitre reste vide (message explicatif).
- [ ] Tests : Vitest + Testing Library (renderers, grading), Playwright (parcours scanner → résolution).

### Phase 2 — V2
- [ ] Défis : catalogue, création, rejoindre par code/lien, chrono, classements, notation, signalement.
- [ ] Renderers `conjugation`, `free_text` (résumé ; affichage de la grille d'évaluation).
- [ ] Gamification : XP, séries, badges.

### Phase 3 — V3 Mobile + matières restantes
- [ ] `apps/mobile` (Expo) : navigation par onglets, auth sécurisée, caméra/scan, réutilisation des renderers (DOM components).
- [ ] Hors-ligne mobile (SQLite) + synchro.
- [ ] Notifications push (révision du jour, défis reçus).
- [ ] Renderers `label_diagram`, `timeline`, `map_locate`, `flashcards` ; dissertation guidée.
- [ ] Publication Play Store (prioritaire), puis App Store.

---

## 8. Règles pour les agents

1. **Lire ce README et les §1, §6, §7 du README backend avant de coder ; mettre à jour le §7 ci-dessus après.** Décision produit manquante → demander au porteur du projet, puis la consigner ici.
2. **Langue** : code en anglais ; **tous les textes d'interface en français**, centralisés (fichier de chaînes) pour rester cohérents.
3. **Jamais de HTML** issu du contenu généré ; texte riche KaTeX uniquement.
4. **Ne jamais afficher la réponse attendue** avant la tentative de l'élève ni hors de la logique d'indices/bilan.
5. **Performance** : vérifier la taille du bundle à chaque ajout de dépendance ; librairies lourdes en chargement différé ; tester en réseau ralenti (profil « Slow 3G ») et sur appareil modeste.
6. **Données** : ne collecter ni stocker aucune donnée personnelle hors téléphone ; pas d'outil d'analytics tiers sans validation.
7. **Contrat de contenu** : `packages/content-schema` doit refléter exactement le §6 du backend ; toute divergence est un bug.
8. **Accessibilité** vérifiée sur chaque composant (navigation clavier sur web, lecteurs d'écran, contrastes, `prefers-reduced-motion`).
9. **Tests** obligatoires pour chaque renderer et chaque mode de correction client.
10. Commits petits et ciblés, format *Conventional Commits*.
