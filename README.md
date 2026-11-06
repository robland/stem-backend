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
- **Python 3.11**, Django 5.2, DRF, SimpleJWT, drf-spectacular (OpenAPI), django-cors-headers.
- **Celery + Redis** (remplace RabbitMQ : plus simple à héberger).
- **PostgreSQL** (SQLite toléré en dev uniquement).
- **Pydantic v2** pour valider le contenu généré par le LLM (schéma §6).
- **SymPy** pour l'équivalence symbolique et la vérification des solutions mathématiques.
- LLM : OpenAI (actuellement `gpt-4.1-mini`) **derrière une couche d'abstraction** `llm/` (provider interchangeable, modèle configurable par tâche via settings).
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

> L'app actuelle `cot_for_stem` sera progressivement scindée dans ces apps (cf. §8, Phase 0/1).

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
- Après génération, chaque étape `symbolic`/`numeric`/`chem_balance` est **revérifiée** ; une étape incohérente déclenche une régénération ciblée (max 2 essais) puis passe en `generation_status = "needs_review"`.

---

## 6. Contrat de contenu : le schéma d'activités

**C'est le contrat central entre backend, LLM et frontend.** Toute modification ⇒ incrémenter `schema_version`, mettre à jour ce README **et** `frontend/README.md`.

### 6.1 Texte riche
Toutes les chaînes affichées sont du **texte riche** : texte simple + LaTeX inline `$...$` / bloc `$$...$$` + chimie via `\ce{...}` (mhchem). **Pas de HTML** (risque XSS) — le prompt actuel qui génère du HTML doit être abandonné. Les backslashes LaTeX sont normaux (`\frac`) : le hack `//` actuel est **interdit**, les *structured outputs* garantissent l'échappement JSON.

### 6.2 Structure d'un parcours (`schema_version: "1.0"`)

```json
{
  "schema_version": "1.0",
  "subject": "maths",
  "chapter_id": "uuid",
  "level": "3e",
  "exam_target": "BEPC",
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
        "prompt": "Complète : $f'(x) = \\placeholder{}$",
        "answer": { "expression": "2x - 4" },
        "grading": "symbolic"
      },
      "hints": ["…", "…", "…"],
      "common_mistakes": [ { "pattern": "2x + 4", "feedback": "Attention au signe de $-4x$." } ],
      "explanation": "…"
    }
  ],
  "summary": { "key_takeaway": "…" }
}
```

### 6.3 Types d'activités

| `type` | Matières | Données clés (`answer` = réponse attendue) | Correction | Version |
|---|---|---|---|---|
| `mcq` | toutes | `options[{id, content}]`, `multiple`, `answer.option_ids` | exact | V1 |
| `true_false` | toutes | `answer.value` | exact | V1 |
| `short_answer` | toutes | `answer.accepted[]`, `normalize` | normalized_text / numeric | V1 |
| `fill_blanks` | toutes | `text` avec `{{1}}`…, `answer.blanks{}` | normalized_text | V1 |
| `matching` | toutes | `left[]`, `right[]`, `answer.pairs` | exact | V1 |
| `ordering` | toutes | `items[]`, `answer.order` | exact | V1 |
| `formula_input` | Maths, PC | `prompt` avec `\placeholder{}`, `answer.expression` | symbolic | V1 |
| `graph_points` | Maths, PC | `axes`, `expected_function`, `points_to_place`, `tolerance` | numeric | V1 |
| `graph_parameters` | Maths, PC | `function` paramétrée, `sliders[]`, question associée | dépend de la question | V1 |
| `variation_table` | Maths | `x_values`, `answer.signs`, `answer.arrows` | exact | V1 |
| `chem_balance` | PC | `reactants[]`, `products[]`, `answer.coefficients` | chem_balance | V1 |
| `chem_formula` | PC | `answer.formula` | exact (normalisé) | V1 |
| `unit_conversion` | PC | `value`, `from_unit`, `to_unit`, `tolerance` | numeric | V1 |
| `conjugation` | Français, Anglais | `verb`, `tense`, `person`, `answer.form` ; feedback radical/terminaison | normalized_text | V2 |
| `free_text` | Français (résumé, dissertation par étapes) | `rubric[]` (critères), `max_words` | llm_rubric | V2 |
| `label_diagram` | SVT | `asset`, `zones[]`, `labels[]`, `answer.mapping` | exact | V3 |
| `timeline` | Histoire-Géo | `events[]`, `answer.dates`, `tolerance_years` | numeric | V3 |
| `map_locate` | Histoire-Géo | `map_id`, `places[]`, `answer.positions`, `tolerance_km` | numeric | V3 |
| `flashcards` | toutes (révision) | `cards[{front, back}]` | auto-évaluation | V3 |

### 6.4 Exposition des réponses
- `GET /api/exercises/{id}` : contenu **sans** `answer`, `common_mistakes`, ni dernier niveau d'indice.
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
| POST | `uploads` | multipart (image/PDF), quota journalier → `{upload_id}` |
| GET | `uploads/{id}` | statut + exercices extraits |
| GET | `uploads/{id}/events` | **SSE** : progression (`reading`, `extracted`, `generating`, `step_ready`, `done`, `error`) |
| PATCH | `extracted-exercises/{id}` | correction énoncé / matière / chapitre |
| POST | `extracted-exercises/{id}/generate` | lance la génération → `{exercise_id}` |
| GET | `exercises` / `exercises/{id}` / `exercises/{id}/offline` | cf. §6.4 |
| POST | `exercises/{id}/attempts` | démarre une tentative |
| POST | `attempts/{id}/answers` | `{step_id, response, client_uuid}` → `{is_correct, feedback}` |
| POST | `attempts/{id}/hints` | `{step_id}` → indice suivant |
| POST | `sync` | lot de tentatives/réponses faites hors-ligne (idempotent via `client_uuid`) |
| GET | `progress` | maîtrise par chapitre, révision du jour |

Le schéma OpenAPI (`/api/schema/`) doit rester **exact** : le front génère son client TypeScript à partir de lui. Toute route doit avoir serializers et annotations drf-spectacular corrects.

---

## 8. État d'avancement

> **Agents : mettez à jour cette section à chaque tâche terminée** (cocher, date `AAAA-MM-JJ`, une ligne de note si utile).
> Dernière mise à jour : 2026-11-06 — Phase 0 terminée (branche `feature/backend-phase0`), 33 tests verts (SQLite local et PostgreSQL Docker).

### Existant (prototype)
- ✅ Auth JWT : inscription (téléphone normalisé + pseudo + mot de passe validé), login (refresh en cookie httpOnly), refresh (cookie **ou** body, rotation + blacklist), logout (blacklist + suppression du cookie). Connexion encore par `username` (passage au téléphone en Phase 1).
- ✅ Tous les endpoints exigent un JWT ; référentiel et exercices en lecture seule ; relance d'analyse réservée aux admins.
- ✅ Upload d'image lié à l'utilisateur + pipeline Celery d'analyse OpenAI (vision) → création `Subject`/`Chapter`/`Exercise`.
- ⚠️ Génération des étapes/QCM : **cassée** (`generate_qcm` itère sur le dict de l'exercice au lieu de `raw_text["steps"]`) — sera remplacée en Phase 1, ne pas corriger isolément.
- ⚠️ PDF envoyés comme image JPEG ; `Document.file_hash` unique globalement (doublon entre élèves) ; `Chapter.name` unique globalement — traités en Phase 1.
- ❌ Réponse aux QCM, progression, hors-ligne, défis.

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
- [ ] Modèle `User` cible (téléphone + pseudo, niveau, série) ; suppression de l'usage nom/prénom.
- [ ] App `curriculum` + fixtures du programme congolais (Maths, PC ; 6e→Tle).
- [ ] App `llm` : client abstrait, prompts versionnés, **structured outputs** (JSON Schema dérivé des modèles Pydantic).
- [ ] App `ingestion` : upload (validation type/taille, hash par utilisateur, quota/jour), extraction vision, édition de l'énoncé, suppression du fichier après validation, support PDF (conversion pages → images).
- [ ] Événements de progression en SSE.
- [ ] App `learning` : génération du parcours (schéma §6, types V1), validation Pydantic, stockage JSON.
- [ ] App `grading` : `exact`, `normalized_text`, `numeric`, `symbolic` (SymPy), `chem_balance` + revérification post-génération.
- [ ] Endpoints tentatives / réponses / indices / offline / sync / progress.
- [ ] Connexion par **téléphone** (`USERNAME_FIELD = "phone"`), `username` → `pseudo`.
- [ ] Quota d'uploads par jour et par utilisateur (throttling DRF).
- [ ] `Mastery` + calcul « révision du jour ».
- [ ] Migration des données/modèles de `cot_for_stem` vers les nouvelles apps (ou reset des migrations si aucune donnée de prod à préserver — **à confirmer avec le porteur du projet**).

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
- [ ] Render : le web est en plan gratuit, mais **le worker Celery exige un plan payant** (bloc commenté dans `render.yaml`). Sans worker, l'analyse des exercices ne tourne pas en production. Alternatives à étudier : autre hébergeur, worker auto-hébergé.
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

Le code est monté en volume : le serveur de dev recharge à chaud ; **redémarrer `worker`** après modification d'une tâche Celery (`docker compose restart worker`).
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
5. **LLM** : uniquement via l'app `llm` ; toujours en structured outputs ; toujours valider par Pydantic ; **jamais d'appel réel au LLM dans les tests** (mocks/fixtures de réponses).
6. **Tests obligatoires** pour toute fonctionnalité : auth/permissions, validation de schéma, chaque moteur de correction, synchro idempotente. Tests dans `<app>/tests/test_*.py`, fixtures communes dans `stem_learning_app/conftest.py`. `docker compose run --rm web pytest` doit être vert avant de considérer une tâche terminée.
7. **Dépendances** : uniquement via `uv add` / `uv remove` (jamais `pip install` dans le projet) ; committer `uv.lock`.
8. **Contrat §6** : toute évolution ⇒ bump `schema_version` + mise à jour des deux README.
9. **OpenAPI** exact et à jour (le front en dépend).
10. **Coûts** : le service est gratuit — dédupliquer (hash), mettre en cache, respecter les quotas, choisir le modèle le moins cher qui tient la qualité.
11. **Secrets** : jamais dans le code ni dans git ; `.env` uniquement.
12. Commits petits et ciblés, format *Conventional Commits* (`feat:`, `fix:`, `refactor:`…).
