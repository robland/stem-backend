# StemLearningApp — Backend (API)

> **Destinataires : agents Claude (et développeurs) qui implémentent le backend.**
> Lisez ce fichier **en entier** avant toute modification. Il fait foi sur le périmètre, les règles et l'état d'avancement.
> Le frontend (web React + mobile) a son propre guide : [`frontend/README.md`](frontend/README.md).

---

## 1. Vision produit

Un élève **photographie son exercice** ; l'application **ne donne pas la réponse** : elle le fait **raisonner étape par étape** (méthode *chain of thought*) via des interactions adaptées à la matière. Une fois l'exercice travaillé, l'élève peut **le partager sous forme de défi** aux autres élèves.

### Contexte (décisions validées)

| Sujet | Décision |
|---|---|
| Public | Élèves de **collège et lycée** |
| Programme | **République du Congo** (Afrique francophone) — préparation **BEPC** (fin de 3e) et **BAC** (Terminale) |
| Niveaux | `6e`, `5e`, `4e`, `3e`, `2nde`, `1re`, `Tle` (+ série au lycée : A, C, D… — liste exacte à confirmer) |
| Matières (cible) | Maths, Physique-Chimie, SVT, Anglais (grammaire, orthographe, conjugaison), Français (conjugaison, résumé, dissertation), Histoire-Géographie (révisions) |
| Langue | **Français uniquement** (interface et contenus générés ; l'anglais n'existe qu'en tant que matière) |
| Modèle économique | **Gratuit** → maîtriser le coût LLM (quotas, cache, déduplication) |
| Parents / enseignants | **Hors périmètre** |
| Données personnelles | **Uniquement** : numéro de téléphone, scores, exercices. Pseudo d'affichage non identifiant. **Aucun** nom, prénom, e-mail, date de naissance, photo de profil. |
| Hors-ligne | **Oui** : un parcours déjà généré doit pouvoir être refait sans connexion (mobile surtout) |
| Clients | Web **React**, puis application **mobile** (React Native + Expo) |

### Contraintes terrain (Congo)
- Connexion souvent lente/instable, données mobiles coûteuses → réponses API **légères**, pagination, compression, pas d'aller-retours inutiles.
- Téléphones Android d'entrée de gamme → le backend fait le travail lourd (OCR, génération, vérification).
- Les images arrivent **déjà redimensionnées** par le client (~1600 px, JPEG), le backend revalide quand même taille et type.

---

## 2. Principes pédagogiques (non négociables)

1. **Guider, ne jamais livrer la solution d'emblée.** Les réponses attendues ne sont jamais renvoyées par les endpoints de consultation (sauf paquet hors-ligne, cf. §6.4).
2. **Structure commune de tout parcours** : Intuition → Rappel (formules/règles) → Micro-étapes interactives (1 étape = 1 compétence) → Bilan.
3. **Indices à 3 niveaux** par étape (coup de pouce → méthode → quasi-solution) ; chaque indice réduit les points.
4. **Correction fiable** : ce qui peut être vérifié par calcul **ne l'est pas par le LLM** (cf. §5).
5. **Ton adapté au niveau** : plus imagé au collège, plus rigoureux au lycée ; vocabulaire et chapitres du programme congolais.

---

## 3. Architecture cible

```
Client (web / mobile)
   │  REST JSON (OpenAPI → client TS généré) + SSE (progression)
   ▼
Django 5.2 + DRF  ──►  PostgreSQL
   │
   ├─► Celery workers (Redis broker)
   │      ├─ extraction  : vision LLM → énoncés structurés
   │      ├─ génération  : LLM (structured outputs) → parcours JSON typé
   │      └─ vérification: SymPy / algorithmes chimie → valide les solutions générées
   └─► Stockage objet (Supabase Storage / S3) pour les uploads (temporaires)
```

### Stack
- **Python 3.12**, Django 5.2, DRF, SimpleJWT, drf-spectacular (OpenAPI), django-cors-headers.
- **Celery + Redis** (remplace RabbitMQ : plus simple à héberger).
- **PostgreSQL** (SQLite toléré en dev uniquement).
- **Pydantic v2** pour valider le contenu généré par le LLM (schéma §6).
- **SymPy** pour l'équivalence symbolique et la vérification des solutions mathématiques.
- LLM : OpenAI (actuellement `gpt-4.1-mini` pour l'extraction, `gpt-4.1` pour la génération) **derrière une couche d'abstraction** `llm/` (provider interchangeable, modèle configurable par tâche via settings).
- Gestion de l'environnement et des dépendances : **uv** (`pyproject.toml` + `uv.lock` versionné ; `uv add` / `uv lock`, jamais de lock régénéré pendant un build).
- **Docker** : `Dockerfile` multi-étapes (`dev` pour Compose/tests, `prod` par défaut : non root, gunicorn, WhiteNoise pour les statiques) ; `docker-compose.yml` = web + worker + PostgreSQL + Redis.
- Settings : `config/settings/{base,dev,prod,test}.py`. `prod` refuse de démarrer sans `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`.

### Arborescence cible

```
stem_learning_app/
├── config/            settings (découpés base/dev/prod), urls, celery, asgi/wsgi
├── accounts/          utilisateur (téléphone + pseudo), auth JWT
├── curriculum/        référentiel programme Congo : matières, niveaux, chapitres (fixtures)
├── ingestion/         uploads, extraction des énoncés, validation par l'élève
├── learning/          parcours (contenu JSON typé), tentatives, réponses, correction, progression
├── grading/           moteurs de correction : déterministe, symbolique (SymPy), chimie, rubric LLM
├── llm/               client LLM abstrait, prompts versionnés, schémas structured outputs
└── challenges/        (V2) défis publics/privés, modération, classements
```

> L'ancienne app `cot_for_stem` a été supprimée au démarrage de la Phase 1 (migrations repartant de zéro) ; son prompt et son service vision restent consultables dans l'historique git (commit `fd1d3ca`).

---

## 4. Modèle de données cible

| Entité | Champs principaux | Notes |
|---|---|---|
| `User` | `phone` (unique, identifiant de connexion), `pseudo` (unique, affiché), `level`, `serie` (nullable), `password` | **Aucun autre champ personnel.** Supprimer `first_name`/`last_name`/`email` de l'usage. |
| `Subject` | `code` (`maths`, `physique_chimie`, `svt`, `francais`, `anglais`, `histoire_geo`), `name` | Référentiel figé (fixture) |
| `Chapter` | `subject`, `level`, `name`, `order` | Unicité `(subject, level, name)` ; fixture du programme congolais |
| `Upload` | `user`, `file`, `file_hash`, `status`, `created_at` | Hash unique **par utilisateur**. **Fichier supprimé après validation de l'extraction** (il peut contenir nom/écriture de l'élève). |
| `ExtractedExercise` | `upload`, `order`, `statement` (texte riche §6.1), `subject`, `chapter`, `level`, `validated_at` | Corrigeable par l'élève avant génération |
| `Exercise` (parcours) | `owner`, `source` (ExtractedExercise), `subject`, `chapter`, `level`, `content` (JSON §6), `schema_version`, `generation_status`, `content_hash` | `content` validé par Pydantic avant enregistrement |
| `Attempt` | `user`, `exercise`, `started_at`, `finished_at`, `score`, `hints_used`, `mode` (`solo`/`challenge`) | |
| `StepAnswer` | `attempt`, `step_id`, `response` (JSON), `is_correct`, `hints_used`, `answered_at`, `client_uuid` (unique) | `client_uuid` rend la synchro hors-ligne **idempotente** |
| `Mastery` | `user`, `chapter`, `score` (0–100), `state` (`non_acquis`/`en_cours`/`maitrise`), `next_review_at` | Répétition espacée |
| `Challenge` (V2) | `exercise`, `author`, `visibility` (`public`/`private`), `code`, `timed`, `hints_allowed`, `status` (modération) | Seul l'énoncé retranscrit est partagé, jamais l'image |

---

## 5. Correction

| Mode | Usage | Où |
|---|---|---|
| `exact` | QCM, vrai/faux, appariement, ordre, frise, carte | Serveur (+ client hors-ligne) |
| `normalized_text` | réponse courte, conjugaison, texte à trous (casse, accents, espaces normalisés selon règle) | Serveur (+ client hors-ligne) |
| `symbolic` | saisie de formule : `2(x+1)` ≡ `2x+2` via **SymPy** | Serveur ; client hors-ligne via équivalent JS (cf. README front) |
| `numeric` | valeur avec tolérance et unité | Serveur (+ client) |
| `chem_balance` | conservation des atomes et des charges | Serveur (+ client) |
| `llm_rubric` | résumé, dissertation, rédaction libre | **Serveur uniquement, en ligne** ; présenté comme un conseil, jamais comme une note sèche |

Règles :
- Le serveur est **la source de vérité** ; un résultat calculé hors-ligne est recalculé à la synchronisation.
- Après génération, le parcours est **revérifié** par `grading.verify.verify_exercise` (expressions lisibles, réponse attendue égale à `answer.source` et sous la forme `answer.form` — une réponse juste mais mal écrite est d'abord réécrite par SymPy depuis `answer.source` (`grading.verify.repair_forms`) —, erreurs typiques ≠ bonne réponse sauf erreur de forme, points sur la courbe, signe de la dérivée dans le tableau de variations, conservation des atomes et des charges, coefficients minimaux, conversions d'unités). Un problème déclenche une régénération ciblée (`GENERATION_ATTEMPTS` = 2 essais au total) puis `generation_status = "needs_review"` (contenu non servi, problèmes dans `Exercise.review_notes`, relecture via l'admin).

### 5.1 Règles de correction (`grading.engine.grade_step`) — à reproduire à l'identique côté client hors-ligne

| Activité | Réponse envoyée (`response`) | Règle |
|---|---|---|
| `mcq` | `{option_ids: [id]}` | ensemble identique à `answer.option_ids` |
| `true_false` | `{value: bool}` | égalité |
| `short_answer` | `{text}` | `normalized_text` : texte normalisé ∈ `accepted` ; `numeric` : nombre lu, `\|v − value\| ≤ tolerance` (unité finale `unit` ignorée) |
| `fill_blanks` | `{blanks: [{id, text}]}` | chaque trou normalisé ∈ ses `accepted` ; `details.blanks` par trou |
| `matching` | `{pairs: [{left_id, right_id}]}` | ensemble identique ; `details.pairs` par élément de gauche |
| `ordering` | `{order: [id]}` | ordre identique |
| `formula_input` | `{expression}` (ASCII, cf. ci-dessous) | équivalence symbolique sur les `answer.variables`, **puis** forme `answer.form` (cf. ci-dessous) ; `details.form = false` si seule la forme est fausse |
| `graph_points` | `{points: [{x, y}]}` | chaque point attendu retrouvé à ± `tolerance` en x et en y, sans point en trop |
| `graph_parameters` | `{values: [{name, value}]}` | chaque paramètre à ± `tolerance` |
| `variation_table` | `{signs: [+\|-], arrows: [up\|down]}` | égalité ; `details.signs` / `details.arrows` |
| `chem_balance` | `{coefficients: [int]}` | atomes **et** charges conservés, **et** plus petits entiers (sinon feedback dédié) |
| `chem_formula` | `{formula}` | écriture normalisée identique (casse comprise : `Co` ≠ `CO`) |
| `unit_conversion` | `{value}` (nombre ou texte) | `\|v − answer.value\| ≤ tolerance × \|answer.value\|` |

- **Texte normalisé** : NFC, apostrophes typographiques → `'`, casse ignorée (`casefold`), espaces multiples réduits, ponctuation finale ` .;!?` retirée. **Les accents comptent.**
- **Nombres** : virgule ou point décimal, espaces de milliers, `2,5×10^3`, `2.5e3`, signe `−` Unicode.
- **Expressions** : ASCII ≤ 200 caractères ; `*` implicite (`2x`, `2(x+1)`, `xy` si x et y sont des variables) ; `^` ou `**` ; fonctions `sqrt sin cos tan exp ln log abs` ; constantes `pi`, `e` ; aucun autre identifiant ; exposants numériques ≤ 100. Équivalence par évaluation en 12 points aléatoires déterministes (tolérance relative 1e-8). Saisie filtrée par liste blanche avant SymPy (`parse_expr` repose sur `eval`).
- **Forme des expressions** (`grading.forms`, sur l'écriture non évaluée de l'élève) : `any` = équivalence seule ; `expanded` = somme de monômes sans parenthèses, termes semblables regroupés, un coefficient par terme (`3x/2` permis, `2*3x`, `x*x` non) ; `factored` = produit (pas une somme au premier niveau), aucun facteur polynomial encore factorisable sur ℚ (`2(x^2 - 1)` non) ; `irreducible_fraction` = entier ou `p/q` avec q > 1 et pgcd(p, q) = 1 (`0.75` non). Réponse équivalente mais de forme fausse → fausse, feedback dédié.
- **Formules chimiques** : éléments du tableau périodique, parenthèses, hydrates `·`, indices Unicode ; charge `^{2+}`, `^2+`, exposants Unicode `²⁺`, ou signe seul (`Na+`) ; électron `e-`.
- **Feedback** : réponse fausse → `common_mistakes` correspondant (formules comparées symboliquement — mais une erreur typique **équivalente** à la réponse, donc une erreur de forme, n'est retenue que pour la même écriture ; nombres numériquement, sinon texte normalisé ; QCM par id ou contenu d'option), sinon feedback spécifique du moteur (forme, lecture de l'expression…) (ex. « Le nombre d'atomes de O n'est pas conservé »), sinon message générique.
- Une réponse mal formée (mauvais type JSON, champ inconnu) est une erreur du client (`InvalidResponse` → HTTP 400), pas une réponse fausse.


### 5.2 Tentatives, indices et score (`learning.attempts`)

- **Parcours guidé** : les étapes se font **dans l'ordre** ; seule l'étape en cours accepte réponses et indices.
- Une étape est **close** quand elle est réussie, ou **échouée** après `ATTEMPT_MAX_WRONG_ANSWERS` (3) réponses fausses. La correction rédigée (`explanation`) n'est renvoyée qu'à la clôture.
- **Indices** : `POST attempts/{id}/hints` donne le niveau suivant (1 → 3) ; le 3ᵉ n'est disponible que par là (absent du contenu public). Hors-ligne, le nombre d'indices consultés est transmis avec chaque réponse (`hints_used`, on garde le maximum).
- **Score d'une étape** (sur 100) : réussie → `max(0, 100 − 20 × indices − 20 × réponses fausses)` ; échouée → 0. **Score de la tentative** = moyenne des étapes (arrondie) ; `finished_at` quand toutes les étapes sont closes.
- **Hors-ligne** : le client génère l'`id` de la tentative et le `client_uuid` de chaque réponse ; `POST sync` rejoue les réponses par `answered_at` (horodatages futurs ramenés à maintenant), **recorrige tout côté serveur** et ignore tout verdict envoyé par le client. Un renvoi ne crée aucun doublon (`duplicate`) ; une réponse refusée (`rejected` + `reason`) ne bloque pas les suivantes. Limites : 50 tentatives et 100 réponses par tentative par appel.


### 5.3 Progression et révision espacée (`learning.progress`)

- **Révision par parcours** (fonctionne sans chapitre) : à partir des scores successifs des tentatives finies, intervalle type Leitner — score ≥ 80 : intervalle doublé (1 jour la première fois, 60 jours max) ; 50–79 : intervalle conservé ; < 50 : 1 jour. Échéance = fin de la dernière tentative + intervalle.
- **Révision du jour** (10 au plus) : d'abord les tentatives commencées non finies (`to_finish`, sauf si une tentative finie plus récente existe), puis les parcours dont l'échéance tombe aujourd'hui ou avant (`to_review`). Seuls les parcours `ready`.
- **Maîtrise par chapitre** (`Mastery`, mise à jour à la fin de chaque tentative, en ligne ou par synchro) : première tentative = son score, puis moyenne mobile `0,6 × ancien + 0,4 × nouveau` ; état `maitrise` ≥ 80, `en_cours` ≥ 40, sinon `non_acquis` ; `next_review_at` = plus proche échéance des parcours du chapitre.
- **Série** (`streak_days`) : jours consécutifs (fuseau `Africa/Brazzaville`) avec au moins une réponse, jusqu'à aujourd'hui ou hier.

---

## 6. Contrat de contenu : le schéma d'activités

**C'est le contrat central entre backend, LLM et frontend.** Toute modification ⇒ incrémenter `schema_version`, mettre à jour ce README **et** `frontend/README.md`.

- **Source de vérité : `llm/schemas/exercise.py`** (Pydantic). `GeneratedExercise` = sortie du LLM ; `ExerciseContent` = contenu stocké (`+ schema_version`, `+ statement`, l'énoncé validé par l'élève, jamais réécrit par le LLM).
- JSON Schema exporté pour le front : `stem_learning_app/schemas/exercise-content.schema.json` (`python manage.py export_content_schema` ; un test échoue s'il n'est pas à jour).
- Les validateurs vérifient la **cohérence interne** (bonne réponse parmi les options, trous ↔ réponses, permutation, un coefficient par espèce, flèches ↔ signes…). Une réponse invalide du LLM est relancée une fois avec la liste des erreurs, puis passe en `error`.

### 6.1 Texte riche
Toutes les chaînes affichées sont du **texte riche** : texte simple + LaTeX inline `$...$` / bloc `$$...$$` + chimie via `\ce{...}` (mhchem). **Pas de HTML** (risque XSS) — le prompt actuel qui génère du HTML doit être abandonné. Les backslashes LaTeX sont normaux (`\frac`) : le hack `//` actuel est **interdit**, les *structured outputs* garantissent l'échappement JSON.

### 6.2 Structure d'un parcours (`schema_version: "1.1"`)

```json
{
  "schema_version": "1.1",
  "title": "Variations d'une fonction du second degré",
  "statement": "Étudier les variations de $f(x) = x^2 - 4x + 3$.",
  "intuition": { "mental_image": "…", "example": "…" },
  "recall": [ { "kind": "formula", "content": "$(x^n)' = n x^{n-1}$", "explanation": "…" } ],
  "steps": [
    {
      "id": "s1",
      "objective": "Calculer la dérivée",
      "skill": "derivation_polynome",
      "activity": {
        "type": "formula_input",
        "grading": "symbolic",
        "prompt": "Complète : $f'(x) = \\placeholder{}$",
        "answer": { "expression": "2*x - 4", "variables": ["x"], "form": "any", "source": null }
      },
      "hints": ["…", "…", "…"],
      "common_mistakes": [ { "pattern": "2x + 4", "feedback": "Attention au signe de $-4x$." } ],
      "explanation": "…"
    }
  ],
  "summary": { "key_takeaway": "…" }
}
```

- Matière, chapitre, niveau et examen visé (`exam` : BEPC pour 6e→3e, BAC pour 2nde→Tle) sont des **champs de l'API** (`Exercise`), pas du contenu.
- Étapes : `id` = `s1`, `s2`… (1 à 10) ; `skill` en snake_case ; **exactement 3 indices** (relance, méthode, quasi-solution) ; 0 à 5 `common_mistakes` ; 0 à 5 `recall`.
- Tous les champs sont toujours présents (`null` quand sans objet) : contrainte des *structured outputs* stricts. Pas d'objet à clés libres : les associations sont des listes.
- Expressions (`answer.expression`, `function`) : syntaxe ASCII lisible par SymPy (`*` explicite, `^`, `sqrt()`, `pi`).
- Historique : **1.1** ajoute `answer.form` et `answer.source` aux `formula_input` (migration `learning.0005` : `form = "any"`, `source = null` pour les parcours 1.0, comportement inchangé).

### 6.3 Types d'activités

Chaque activité porte `type`, `grading` et `prompt` (consigne, texte riche).

| `type` | Matières | Données clés (`answer` = réponse attendue) | Correction | Version |
|---|---|---|---|---|
| `mcq` | toutes | `options[{id, content}]` (2–6), `multiple`, `answer.option_ids` | exact | V1 |
| `true_false` | toutes | `answer.value` | exact | V1 |
| `short_answer` | toutes | `answer.accepted[]` (texte) ou `answer.value` + `tolerance` (absolue) + `unit` (numérique) | normalized_text / numeric | V1 |
| `fill_blanks` | toutes | `text` avec `{{1}}`…, `answer.blanks[{id, accepted[]}]` | normalized_text | V1 |
| `matching` | toutes | `left[{id, content}]`, `right[…]`, `answer.pairs[{left_id, right_id}]` | exact | V1 |
| `ordering` | toutes | `items[{id, content}]` (mélangés par le client), `answer.order[ids]` | exact | V1 |
| `formula_input` | Maths, PC | `prompt` avec exactement un `\placeholder{}`, `answer.expression`, `answer.variables`, `answer.form` (`any` / `expanded` / `factored` / `irreducible_fraction`) | symbolic | V1 |
| `graph_points` | Maths, PC | `axes`, `points_to_place[x]`, `tolerance`, `answer.function`, `answer.points[{x, y}]` | numeric | V1 |
| `graph_parameters` | Maths, PC | `axes`, `function` paramétrée (`a*x + b`), `sliders[{name, min, max, step, initial}]`, `tolerance`, `answer.values[{name, value}]` | numeric | V1 |
| `variation_table` | Maths | `x_values` (texte riche), `answer.signs` (`+`/`-`), `answer.arrows` (`up`/`down`), un par intervalle, `answer.function` (optionnel) | exact | V1 |
| `chem_balance` | PC | `reactants[]`, `products[]`, `answer.coefficients` | chem_balance | V1 |
| `chem_formula` | PC | `answer.formula` | exact (normalisé) | V1 |
| `unit_conversion` | PC | `value`, `from_unit`, `to_unit`, `tolerance` (relative), `answer.value` | numeric | V1 |
| `conjugation` | Français, Anglais | `verb`, `tense`, `person`, `answer.form` ; feedback radical/terminaison | normalized_text | V2 |
| `free_text` | Français (résumé, dissertation par étapes) | `rubric[]` (critères), `max_words` | llm_rubric | V2 |
| `label_diagram` | SVT | `asset`, `zones[]`, `labels[]`, `answer.mapping` | exact | V3 |
| `timeline` | Histoire-Géo | `events[]`, `answer.dates`, `tolerance_years` | numeric | V3 |
| `map_locate` | Histoire-Géo | `map_id`, `places[]`, `answer.positions`, `tolerance_km` | numeric | V3 |
| `flashcards` | toutes (révision) | `cards[{front, back}]` | auto-évaluation | V3 |

### 6.4 Exposition des réponses
- `GET /api/exercises/{id}` : contenu **sans** `activity.answer`, `common_mistakes`, `explanation` (la correction rédigée), ni dernier niveau d'indice (`learning.services.public_content`).
- `GET /api/exercises/{id}/offline` : contenu **complet**, réservé au **propriétaire** du parcours (pas aux défis) pour la correction hors-ligne.
- Défis : correction **toujours côté serveur, en ligne**.

---

## 7. API cible (V1)

Préfixe `/api/`. Auth : JWT Bearer (access 15 min) ; refresh token en cookie httpOnly (web) ou stockage sécurisé (mobile → le refresh est aussi accepté dans le body).

| Méthode | Route | Rôle |
|---|---|---|
| POST | `auth/register` | `{phone, pseudo, password, level, serie?}` |
| POST | `auth/login` / `auth/refresh` / `auth/logout` | |
| GET/PATCH | `me` | niveau, série, pseudo |
| GET | `curriculum/subjects`, `curriculum/chapters?subject=&level=` | référentiel |
| POST | `uploads` | multipart `file` (JPEG/PNG/WebP/PDF ≤ 4 pages, ≤ 10 Mo) → `201` upload ; `200` si le même document a déjà été envoyé (idempotent, hors quota) ; `429` + `Retry-After` si quota journalier atteint |
| GET | `uploads/{id}` | `status` (`pending` → `reading` → `extracted` \| `error`), `error_message` (destiné à l'élève), exercices extraits. Aucune URL de fichier exposée |
| GET | `uploads/{id}/events` | **SSE** : progression (`reading`, `extracted`, `generating`, `step_ready`, `done`, `error`) |
| PATCH / DELETE | `extracted-exercises/{id}` | correction (`statement`, `subject`, `level`, `chapter`) / écarter un énoncé — refusé (`400`) une fois validé |
| POST | `extracted-exercises/{id}/validate` | fige l'énoncé (matière et niveau requis) ; fichier d'origine supprimé quand tous les énoncés sont validés |
| POST | `extracted-exercises/{id}/generate` | énoncé validé requis → `202` génération lancée ; `200` parcours existant ou repris du cache ; `400` matière non ouverte ; `429` quota journalier. Réponse = parcours (`id`, `generation_status`…) |
| GET | `exercises` (pagination par curseur, 20) / `exercises/{id}` / `exercises/{id}/offline` | cf. §6.4 ; `content` vaut `null` tant que `generation_status` ≠ `ready` |
| POST | `exercises/{id}/attempts` | `{id?, started_at?}` → `201` tentative (`200` si `id` déjà créé) ; parcours `ready` requis |
| GET | `attempts/{id}` | score, indices, `current_step_id`, état de chaque étape (`pending` / `succeeded` / `failed`) |
| POST | `attempts/{id}/answers` | `{step_id, response, client_uuid, answered_at?, hints_used?}` → `{is_correct, feedback, details, step, explanation, attempt}` ; `201`, ou `200` si `client_uuid` déjà reçu |
| POST | `attempts/{id}/hints` | `{step_id}` → `{hint, level, total}` (étape en cours uniquement) |
| POST | `sync` | `{attempts: [{id, exercise, started_at, answers: [...]}]}` → statut par tentative et par réponse (cf. §5.2) |
| GET | `progress` | `summary` (parcours faits, tentatives, score moyen, série de jours), `subjects`, `chapters` (maîtrise), `review_today` (cf. §5.3) |

Le schéma OpenAPI (`/api/schema/`) doit rester **exact** : le front génère son client TypeScript à partir de lui. Toute route doit avoir serializers et annotations drf-spectacular corrects.

---

## 8. État d'avancement

> **Agents : mettez à jour cette section à chaque tâche terminée** (cocher, date `AAAA-MM-JJ`, une ligne de note si utile).
> Dernière mise à jour : 2026-11-06 — Phase 1 en cours (branche `feature/backend-phase1`) : modèle de données, app `llm`, pipeline d'ingestion (upload → extraction → validation), génération des parcours, moteurs de correction, tentatives et synchro hors-ligne, progression, tâches périodiques ; 438 tests verts.

### Existant
- ✅ Auth JWT par **téléphone** : inscription (téléphone normalisé, pseudo, niveau obligatoire, série optionnelle, mot de passe validé), login (refresh en cookie httpOnly), refresh (cookie **ou** body, rotation + blacklist), logout.
- ✅ `GET/PATCH /api/me/` (pseudo, niveau, série ; téléphone non modifiable).
- ✅ Référentiel `GET /api/curriculum/subjects/` et `/api/curriculum/chapters/?subject=&level=` (lecture seule) ; 6 matières créées par migration.
- ✅ Modèles `ingestion` (`Upload`, `ExtractedExercise`) et `learning` (`Exercise`, `Attempt`, `StepAnswer`, `Mastery`) avec contraintes (hash unique par élève, `client_uuid` unique, une maîtrise par chapitre, score ≤ 100) ; admin Django pour tous.
- ✅ Upload → extraction asynchrone → correction/validation des énoncés (`/api/uploads/`, `/api/extracted-exercises/`).
- ✅ Génération des parcours (Maths, PC) : schéma §6 validé, relance corrective, cache par énoncé, quota ; consultation sans réponses et paquet hors-ligne.
- ✅ Moteurs de correction et revérification des parcours (`grading`).
- ✅ Tentatives : démarrage, réponses corrigées avec feedback, indices, score, synchronisation hors-ligne idempotente.
- ✅ Progression : maîtrise par chapitre, révision espacée par parcours, révision du jour, série de jours (`/api/progress/`).
- ❌ SSE, défis.

### Phase 0 — Assainissement ✅ (2026-11-06)
- [x] Sécurité : `JWTAuthentication` + `IsAuthenticated` par défaut ; viewsets en lecture seule ; `process_document` réservé aux admins (POST) ; `process_exercise` (debug cassé) supprimé ; `correct_choice` retiré de `QCMSerializer`.
- [x] `token_blacklist` installé ; `RefreshView` : refresh lu dans le body (mobile) ou le cookie (web), nouveau refresh renvoyé par le même canal.
- [x] `logout/` : vue DRF, blacklist du refresh, suppression du cookie (204).
- [x] Settings `base/dev/prod/test` ; secrets uniquement par variables d'environnement (`.env` à la racine, cf. `.env.example`) ; `ALLOWED_HOSTS`/CORS par variables ; `MEDIA_ROOT` défini ; code Supabase mort retiré ; langue `fr-fr`, fuseau `Africa/Brazzaville`.
- [x] Poetry → **uv** ; psycopg 3 ; broker **Redis** ; WhiteNoise pour les statiques en prod.
- [x] Docker : Dockerfile multi-étapes (dev/prod), docker-compose (web, worker, PostgreSQL, Redis), `render.yaml` en runtime Docker ; `build.sh` supprimé.
- [x] Hygiène git : `db.sqlite3`, `openai.response.json`, `.idea/`, `historic_commands`, `prompt_recherche_emploi`, `poetry.lock` retirés du suivi ; `.gitignore` réécrit.
- [x] pytest-django : `conftest.py` (fixtures `api_client`, `user`, `auth_client`, `admin_client`), tests auth + sécurité de l'API (33 tests).
- [x] Corrections ponctuelles : filtre `ExerciseView` (non réassigné), `context` passé au serializer (`solved`), upload lié à `request.user` et `request.FILES`, client OpenAI créé à la demande, plus d'écriture de `openai.response.json`, plus d'affichage de la clé OpenAI dans Celery.

### Phase 1 — V1 backend (Maths + Physique-Chimie)
- [x] Modèle `User` cible (`AbstractBaseUser` : téléphone, pseudo, niveau, série ; aucun nom/prénom/e-mail) + `/api/me/` — 2026-11-06.
- [x] App `curriculum` : `Subject` (codes figés, seed par migration), `Chapter` unique par (matière, niveau, nom), API en lecture seule — 2026-11-06.
- [ ] **Chapitres du programme congolais** (Maths, PC ; 6e→Tle) : à saisir à partir des programmes officiels fournis par le porteur du projet (ne pas inventer), puis data migration ou fixture.
- [x] App `llm` : client abstrait `LLMClient` (`OpenAIClient` via `chat.completions.parse`, `FakeLLMClient` pour les tests), modèle par tâche (`LLM_MODELS`), prompts versionnés immuables (`extraction.v1`), schémas Pydantic compatibles structured outputs stricts, type `RichText` (HTML refusé), service `extract_exercises(images, declared_level)` — 2026-11-06.
- [x] Schéma de contenu §6 en Pydantic (13 types V1, validateurs de cohérence, compatible mode strict) + prompt `generation.v1` + `generate_exercise` avec relance corrective + export JSON Schema — 2026-11-06.
- [x] Modèles `ingestion` et `learning` (§4) — 2026-11-06.
- [x] App `ingestion` — 2026-11-06 :
  - upload : type détecté par le contenu, taille ≤ `UPLOAD_MAX_BYTES`, PDF ≤ `UPLOAD_MAX_PDF_PAGES` (pypdfium2), hash SHA-256 par élève (renvoi idempotent ; un upload en erreur peut être renvoyé), nom de fichier aléatoire ;
  - extraction Celery (`ingestion.tasks.extract_upload`, idempotente) : pages → JPEG ≤ 2048 px, orientation appliquée, **EXIF supprimés** ; correspondance de chapitre par `chapter_hint` (sinon conservé en texte) ; erreurs traduites en messages pour l'élève ;
  - correction / suppression / validation des énoncés (mêmes règles `ExerciseStatement` que le LLM) ;
  - fichier supprimé quand tous les énoncés sont validés, en cas d'erreur, ou après `UPLOAD_FILE_RETENTION_HOURS` (`manage.py purge_upload_files` / tâche `purge_expired_upload_files`).
- [ ] Événements de progression en SSE.
- [x] App `learning` : génération asynchrone (`learning.tasks.generate_exercise_task`, idempotente), un parcours par énoncé (relance si erreur), cache inter-élèves par `content_hash` (énoncé normalisé + matière + niveau), quota `GENERATION_DAILY_QUOTA` (copies du cache non comptées), matières ouvertes `GENERATION_SUBJECTS` ; API `exercises` — 2026-11-06.
- [x] App `grading` : moteurs pour les 13 types V1 (texte normalisé, nombres FR/EN, équivalence symbolique SymPy sécurisée, chimie atomes + charges + électrons, unités), feedback par erreurs typiques, revérification post-génération intégrée à `learning` (`needs_review`, `review_notes`) — 2026-11-06.
- [x] Endpoints tentatives / réponses / indices / sync (`learning.attempts`, §5.2) — 2026-11-06.
- [x] Connexion par **téléphone** (`USERNAME_FIELD = "phone"`), `username` → `pseudo` — 2026-11-06.
- [x] Quota d'uploads par jour et par élève (`UPLOAD_DAILY_QUOTA`, jour calendaire `Africa/Brazzaville`, compté en base plutôt que par throttling DRF pour ne pas décompter les fichiers refusés) — 2026-11-06.
- [x] Tâches périodiques — 2026-11-06 :
  - `CELERY_BEAT_SCHEDULE` : `ingestion.tasks.run_maintenance` toutes les 5 min, purge des fichiers expirés toutes les heures ; service `beat` dans Compose (un seul processus beat).
  - traitement bloqué = sans nouvelle depuis `JOB_STUCK_AFTER_MINUTES` (15, > `CELERY_TASK_TIME_LIMIT`) : `pending` → relancé (tâches idempotentes) ; `reading` / `generating` → `error` avec message (pas de relance automatique : un document qui fait planter le worker bouclerait). L'élève renvoie le document ou relance la génération (sans quota supplémentaire).
  - sans beat (cron d'hébergeur) : `python manage.py run_maintenance` (bloc `cron` commenté dans `render.yaml`).
- [x] `Mastery` + révision espacée + « révision du jour » + endpoint `progress` (§5.3) — 2026-11-06.
- [x] Reset des migrations (décision du porteur du projet : aucune donnée à conserver) ; `cot_for_stem` supprimée — 2026-11-06.

### Essai réel des prompts (2026-11-07)

Fiche de maths 3e photographiée (en-tête avec nom et établissement) + PDF de PC 2nde de 2 pages ; 4 exercices. Documents de synthèse : **l'écriture manuscrite reste à tester sur de vraies photos.**

| | `gpt-4.1-mini` | `gpt-4.1` (génération seule) |
|---|---|---|
| Extraction `extraction.v2` | ✅ 4/4 exercices, ordre, matière, niveau (2nde lu dans l'en-tête), aucune donnée personnelle, formules en `$…$` (après 1 relance sur la photo) | — |
| Génération `generation.v2` | ❌ 1/4 parcours valide (formules hors `$…$`, tableau de variations faux, `fill_blanks` sans trou) | ✅ 3/4 produits : 2 `ready`, 1 `needs_review` (erreur typique équivalente à la réponse) ; 1 échec (tableau de variations faux) |
| Coût estimé (tarifs publics, relances comprises) | ≈ 0,005 $ par parcours | ≈ 0,03 $ par parcours |

Corrections issues de l'essai : `extraction.v2` / `generation.v2` (exemples de texte riche, niveau de l'en-tête, nombre de questions annoncé au modèle, trous hors `$…$`), `LLMRichText` (sortie LLM : aucune commande LaTeX, `^`, `_`, exposant ou indice Unicode hors `$…$` / `\ce{}`, unités `m²`/`cm³` permises), relance corrective de l'extraction, contrôle de couverture (≥ 1 étape par question numérotée), journalisation des échecs d'appel.

Réparations côté serveur (essais suivants, `gpt-4.1` + `generation.v3`, journal `erreur_schema=`) : zone de saisie `\placeholder{}` ajoutée en fin de consigne `formula_input` quand elle manque ; formule du rappel (`recall`, `kind = formula`) sans aucun mot entourée de `$…$` ; calcul faux détecté par `answer.source` → relance avec le bon résultat calculé par SymPy. Résultat sur « développer et réduire » : 2 parcours justes sur 2, en 2 appels chacun (au lieu de 4 appels et un échec).

À décider / à faire :
- [x] **Modèle de génération** : `gpt-4.1` retenu (nettement plus fiable, ≈ 6× plus cher ; le cache entre élèves amortit les sujets récurrents). Réglable par `LLM_MODEL_GENERATION`.
- [x] Forme attendue des réponses : `answer.form` (`expanded`, `factored`, `irreducible_fraction`) ajouté au contrat (schéma 1.1, prompt `generation.v3`) ; une forme non réduite est refusée avec un feedback dédié. `answer.source` (expression de départ recopiée de l'énoncé) permet à la revérification de détecter un calcul faux du LLM : au 2e essai, `gpt-4.1` attendait `3x² + 10x + 8` pour `(2x+3)² − (x−1)(x+5)` (= `3x² + 8x + 14`).
- [ ] Rejouer l'essai sur de vraies photos (manuscrit, mauvais éclairage) avant la mise en production.

### Phase 2 — V2
- [ ] App `challenges` : défis publics (catalogue matière/chapitre/niveau) et privés (code/lien), chrono, indices on/off, notation, points auteur.
- [ ] Modération : filtrage automatique LLM, signalements, déduplication des énoncés (`content_hash`).
- [ ] Français & Anglais : `conjugation`, `free_text` + grading `llm_rubric` (résumé), référentiel chapitres.

### Phase 3 — V3
- [ ] SVT (`label_diagram`, assets de schémas), Histoire-Géo (`timeline`, `map_locate`, fiches de révision, `flashcards`).
- [ ] Dissertation guidée (problématique → plan → arguments → exemples).
- [ ] Notifications push (rappels de révision, défis reçus) — endpoint d'enregistrement des tokens Expo.
- [ ] Login mobile : renvoyer le refresh token dans le body (le refresh/logout l'acceptent déjà).

### Déploiement (à décider)
- [ ] Render : le web est en plan gratuit, mais **le worker Celery exige un plan payant** (bloc commenté dans `render.yaml`), de même que les tâches périodiques (worker lancé avec `-B`, ou cron job `run_maintenance`). Sans worker, l'analyse des exercices ne tourne pas en production. Alternatives à étudier : autre hébergeur, worker auto-hébergé.
- [ ] Stockage des uploads en prod (disque Render éphémère) : stockage objet S3-compatible (Supabase Storage).

---

## 9. Lancer le projet

### Avec Docker (recommandé)

```bash
cp .env.example .env                       # compléter OPENAI_API_KEY (le reste a des valeurs par défaut en dev)
docker compose up --build                  # API : http://localhost:8000/api/ — Swagger : /api/schema/swagger-ui/
docker compose run --rm web pytest         # tests sur PostgreSQL
docker compose run --rm web python manage.py createsuperuser
```

Services : `web` (API), `worker` (extraction, génération), `beat` (tâches périodiques), `db`, `redis`.
Le code est monté en volume : le serveur de dev recharge à chaud ; **redémarrer `worker` et `beat`** après modification d'une tâche Celery ou de `CELERY_BEAT_SCHEDULE` (`docker compose restart worker beat`).
Après un changement de dépendances : `uv add <paquet>` (ou `uv lock`) puis `docker compose build`.

### Sans Docker

```bash
uv sync                                    # crée .venv avec les dépendances (dont dev)
cp .env.example .env
uv run pytest                              # tests (SQLite en mémoire)
cd stem_learning_app
uv run python manage.py migrate
uv run python manage.py runserver
uv run celery -A config worker -l info     # nécessite Redis sur localhost:6379
uv run celery -A config beat -l info       # tâches périodiques (ou : manage.py run_maintenance)
```

### Image de production

```bash
docker build -t stem-backend .             # cible prod par défaut
docker run -p 8000:8000 -e SECRET_KEY=... -e ALLOWED_HOSTS=... -e DATABASE_URL=... stem-backend
# worker : même image, commande `celery -A config worker -l info`
```

Les tests utilisent toujours `config.settings.test` (forcé par `--ds` dans `pyproject.toml`) : `DATABASE_URL` est ignoré, seule `TEST_DATABASE_URL` (Docker) ou SQLite en mémoire est utilisée.

---

## 10. Règles pour les agents

1. **Lire ce README avant de coder ; le mettre à jour (§8) après.** Si une décision produit manque, demander au porteur du projet plutôt que l'inventer ; noter la décision ici une fois prise.
2. **Langue** : identifiants de code en anglais ; textes visibles par l'élève, prompts et documentation en français.
3. **Données personnelles** : n'ajoutez **jamais** de champ personnel au-delà du téléphone. Ne loggez ni numéros de téléphone, ni contenus d'uploads.
4. **Réponses attendues** : ne jamais les exposer hors de l'endpoint `offline` réservé au propriétaire.
5. **LLM** : uniquement via l'app `llm` ; toujours en structured outputs ; toujours valider par Pydantic ; **jamais d'appel réel au LLM dans les tests** : les settings de test imposent `FakeLLMClient`, piloté par la fixture `fake_llm` (`fake_llm.queue({...})`, `fake_llm.calls`).
   - Les autres apps n'appellent que `llm/services.py` (jamais le SDK directement).
   - Un prompt publié ne se modifie pas : créer `Prompt(name, version+1)` et l'enregistrer dans `llm/prompts/__init__.py` ; conserver le `prompt_id` avec le contenu produit.
   - Schémas de sortie : pas de valeurs par défaut, `extra="forbid"`, contraintes de longueur/nombre via validateurs Pydantic (refusées par le mode strict) ; `llm/tests/test_schemas.py` vérifie la compatibilité.
   - Ne jamais logger le contenu des prompts ni des réponses : uniquement les métriques (tâche, prompt, modèle, tokens, durée).
6. **Tests obligatoires** pour toute fonctionnalité : auth/permissions, validation de schéma, chaque moteur de correction, synchro idempotente. Tests dans `<app>/tests/test_*.py`, fixtures communes dans `stem_learning_app/conftest.py`. `docker compose run --rm web pytest` doit être vert avant de considérer une tâche terminée.
7. **Dépendances** : uniquement via `uv add` / `uv remove` (jamais `pip install` dans le projet) ; committer `uv.lock`.
8. **Contrat §6** : toute évolution ⇒ bump `schema_version` + mise à jour des deux README.
9. **OpenAPI** exact et à jour (le front en dépend).
10. **Coûts** : le service est gratuit — dédupliquer (hash), mettre en cache, respecter les quotas, choisir le modèle le moins cher qui tient la qualité.
11. **Secrets** : jamais dans le code ni dans git ; `.env` uniquement.
12. Commits petits et ciblés, format *Conventional Commits* (`feat:`, `fix:`, `refactor:`…).
