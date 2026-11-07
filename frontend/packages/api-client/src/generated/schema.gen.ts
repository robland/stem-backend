// Fichier généré par scripts/generate.mjs depuis /api/schema/ — ne pas modifier (`pnpm api:generate`).
export interface paths {
  "/api/attempts/{id}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["attempts_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/attempts/{id}/answers/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Envoyer la réponse à l'étape en cours */
    post: operations["attempts_answers_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/attempts/{id}/hints/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Obtenir l'indice suivant de l'étape en cours
     * @description Chaque indice consulté réduit le score de l'étape (README §5.2).
     */
    post: operations["attempts_hints_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/auth/login/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** @description Renvoie l'access token ; le refresh token est posé en cookie httpOnly. */
    post: operations["auth_login_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/auth/logout/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** @description Invalide le refresh token (body ou cookie) et supprime le cookie. */
    post: operations["auth_logout_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/auth/refresh/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * @description Accepte le refresh token dans le body (mobile) ou dans le cookie (web).
     *     Le nouveau refresh token (rotation) est renvoyé par le même canal.
     */
    post: operations["auth_refresh_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/auth/register/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: operations["auth_register_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/curriculum/chapters/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["curriculum_chapters_list"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/curriculum/chapters/{id}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["curriculum_chapters_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/curriculum/subjects/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["curriculum_subjects_list"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/curriculum/subjects/{code}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["curriculum_subjects_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/exercises/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Mes parcours */
    get: operations["exercises_list"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/exercises/{id}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Parcours sans les réponses attendues */
    get: operations["exercises_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/exercises/{id}/attempts/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Démarrer une tentative */
    post: operations["exercises_attempts_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/exercises/{id}/events/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Suivre la génération en direct (SSE) */
    get: operations["exercises_events_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/exercises/{id}/offline/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /**
     * Parcours complet pour la correction hors-ligne
     * @description Inclut les réponses attendues : réservé au propriétaire du parcours, jamais aux défis.
     */
    get: operations["exercises_offline_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/extracted-exercises/{id}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    /** Écarter un énoncé extrait non validé */
    delete: operations["extracted_exercises_destroy"];
    options?: never;
    head?: never;
    /** Corriger un énoncé extrait (matière, niveau, chapitre) */
    patch: operations["extracted_exercises_partial_update"];
    trace?: never;
  };
  "/api/extracted-exercises/{id}/generate/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Générer le parcours guidé d'un énoncé validé
     * @description Suivre l'avancement via `GET /api/exercises/{id}/`.
     */
    post: operations["extracted_exercises_generate_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/extracted-exercises/{id}/validate/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Valider un énoncé extrait
     * @description Le document d'origine est supprimé dès que tous ses énoncés sont validés.
     */
    post: operations["extracted_exercises_validate_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/me/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** @description Profil de l'élève connecté (niveau, série, pseudo). */
    get: operations["me_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** @description Profil de l'élève connecté (niveau, série, pseudo). */
    patch: operations["me_partial_update"];
    trace?: never;
  };
  "/api/progress/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Ma progression et ma révision du jour */
    get: operations["progress_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/sync/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Synchroniser les tentatives faites hors-ligne
     * @description Idempotent : les tentatives (id) et réponses (client_uuid) déjà reçues ne sont pas dupliquées. Le serveur recorrige chaque réponse ; son verdict fait foi.
     */
    post: operations["sync_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/uploads/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /**
     * Envoyer un document d'exercices
     * @description L'extraction est asynchrone : suivre `status` via `GET /api/uploads/{id}/`.
     */
    post: operations["uploads_create"];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/uploads/{id}/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: operations["uploads_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  "/api/uploads/{id}/events/": {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Suivre l'extraction en direct (SSE) */
    get: operations["uploads_events_retrieve"];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    AccessToken: {
      access: string;
    };
    AnswerCreate: {
      step_id: string;
      /** @description Format selon le type d'activité (README §5.1). */
      response: unknown;
      /**
       * Format: uuid
       * @description Généré par le client : un renvoi ne crée pas de doublon.
       */
      client_uuid: string;
      /** Format: date-time */
      answered_at?: string;
      /** @description Indices consultés hors-ligne pour cette étape. */
      hints_used?: number;
    };
    AnswerResult: {
      is_correct: boolean;
      feedback: string | null;
      /** @description Détail par élément (trous, points, paires…). */
      details: {
        [key: string]: unknown;
      };
      step: components["schemas"]["StepState"];
      /** @description Correction rédigée, une fois l'étape close. */
      explanation: string | null;
      attempt: components["schemas"]["Attempt"];
    };
    Attempt: {
      /** Format: uuid */
      readonly id: string;
      /** Format: uuid */
      readonly exercise: string;
      readonly mode: components["schemas"]["ModeEnum"];
      /** Format: date-time */
      readonly started_at: string;
      /** Format: date-time */
      readonly finished_at: string | null;
      readonly score: number;
      readonly hints_used: number;
      /** @description Étape à traiter ; null si la tentative est finie. */
      readonly current_step_id: string | null;
      readonly steps: components["schemas"]["StepState"][];
    };
    AttemptStart: {
      /**
       * Format: uuid
       * @description Généré par le client (hors-ligne) : rend l'appel idempotent.
       */
      id?: string;
      /** Format: date-time */
      started_at?: string;
    };
    /** @enum {unknown} */
    BlankEnum: "";
    Chapter: {
      /** Format: uuid */
      readonly id: string;
      readonly subject: components["schemas"]["SubjectCodeEnum"];
      level: components["schemas"]["LevelEnum"];
      name: string;
      order?: number;
    };
    Exercise: {
      /** Format: uuid */
      readonly id: string;
      readonly title: string;
      readonly subject: components["schemas"]["SubjectCodeEnum"];
      /** Format: uuid */
      readonly chapter: string | null;
      readonly level: components["schemas"]["LevelEnum"];
      /** @description Examen visé : BEPC (collège) ou BAC (lycée). */
      readonly exam: string;
      readonly generation_status: components["schemas"]["GenerationStatusEnum"];
      readonly error_message: string;
      /** Format: date-time */
      readonly created_at: string;
    };
    ExerciseDetail: {
      /** Format: uuid */
      readonly id: string;
      readonly title: string;
      readonly subject: components["schemas"]["SubjectCodeEnum"];
      /** Format: uuid */
      readonly chapter: string | null;
      readonly level: components["schemas"]["LevelEnum"];
      /** @description Examen visé : BEPC (collège) ou BAC (lycée). */
      readonly exam: string;
      readonly generation_status: components["schemas"]["GenerationStatusEnum"];
      readonly error_message: string;
      /** Format: date-time */
      readonly created_at: string;
      readonly schema_version: string;
      /** @description Parcours (README §6, JSON Schema dans schemas/exercise-content.schema.json) sans les champs qui donnent la réponse : activity.answer, common_mistakes, explanation, dernier indice. null tant que le parcours n'est pas prêt. */
      readonly content: {
        [key: string]: unknown;
      } | null;
      /**
       * Format: uuid
       * @description Tentative commencée et non finie à reprendre (détail : GET /api/attempts/{id}/) ; null sinon.
       */
      readonly current_attempt: string | null;
    };
    ExerciseOffline: {
      /** Format: uuid */
      readonly id: string;
      readonly title: string;
      readonly subject: components["schemas"]["SubjectCodeEnum"];
      /** Format: uuid */
      readonly chapter: string | null;
      readonly level: components["schemas"]["LevelEnum"];
      /** @description Examen visé : BEPC (collège) ou BAC (lycée). */
      readonly exam: string;
      readonly generation_status: components["schemas"]["GenerationStatusEnum"];
      readonly error_message: string;
      /** Format: date-time */
      readonly created_at: string;
      readonly schema_version: string;
      /** @description Parcours (README §6, JSON Schema dans schemas/exercise-content.schema.json) sans les champs qui donnent la réponse : activity.answer, common_mistakes, explanation, dernier indice. null tant que le parcours n'est pas prêt. */
      readonly content: {
        [key: string]: unknown;
      } | null;
      /**
       * Format: uuid
       * @description Tentative commencée et non finie à reprendre (détail : GET /api/attempts/{id}/) ; null sinon.
       */
      readonly current_attempt: string | null;
    };
    ExtractedExercise: {
      /** Format: uuid */
      readonly id: string;
      readonly order: number;
      statement: string;
      subject?: components["schemas"]["SubjectCodeEnum"] | null;
      /** Format: uuid */
      chapter?: string | null;
      readonly chapter_hint: string;
      level?: components["schemas"]["LevelEnum"] | components["schemas"]["BlankEnum"];
      /** Format: date-time */
      readonly validated_at: string | null;
    };
    /**
     * @description * `image` - Image
     *     * `pdf` - PDF
     * @enum {string}
     */
    FileTypeEnum: "image" | "pdf";
    /**
     * @description * `pending` - En attente
     *     * `generating` - Génération
     *     * `ready` - Prêt
     *     * `needs_review` - À revoir
     *     * `error` - Erreur
     * @enum {string}
     */
    GenerationStatusEnum: "pending" | "generating" | "ready" | "needs_review" | "error";
    Hint: {
      step_id: string;
      hint: string;
      level: number;
      total: number;
    };
    HintRequest: {
      step_id: string;
    };
    /**
     * @description * `6e` - 6e
     *     * `5e` - 5e
     *     * `4e` - 4e
     *     * `3e` - 3e
     *     * `2nde` - 2nde
     *     * `1re` - 1re
     *     * `Tle` - Terminale
     * @enum {string}
     */
    LevelEnum: "6e" | "5e" | "4e" | "3e" | "2nde" | "1re" | "Tle";
    /** @description Documentation OpenAPI de `auth/login` (la validation reste celle de SimpleJWT). */
    Login: {
      phone: string;
      password: string;
    };
    Mastery: {
      chapter: components["schemas"]["Chapter"];
      score?: number;
      state?: components["schemas"]["StateEnum"];
      /** Format: date-time */
      next_review_at?: string | null;
      /** Format: date-time */
      readonly updated_at: string;
    };
    Me: {
      readonly phone: string;
      pseudo: string;
      level?: components["schemas"]["LevelEnum"] | components["schemas"]["BlankEnum"];
      serie?: components["schemas"]["SerieEnum"] | components["schemas"]["BlankEnum"];
      /** Format: date-time */
      readonly date_joined: string;
    };
    /**
     * @description * `solo` - Solo
     *     * `challenge` - Défi
     * @enum {string}
     */
    ModeEnum: "solo" | "challenge";
    PaginatedExerciseList: {
      /**
       * Format: uri
       * @example http://api.example.org/accounts/?cursor=cD00ODY%3D"
       */
      next?: string | null;
      /**
       * Format: uri
       * @example http://api.example.org/accounts/?cursor=cj0xJnA9NDg3
       */
      previous?: string | null;
      results: components["schemas"]["Exercise"][];
    };
    PatchedExtractedExercise: {
      /** Format: uuid */
      readonly id?: string;
      readonly order?: number;
      statement?: string;
      subject?: components["schemas"]["SubjectCodeEnum"] | null;
      /** Format: uuid */
      chapter?: string | null;
      readonly chapter_hint?: string;
      level?: components["schemas"]["LevelEnum"] | components["schemas"]["BlankEnum"];
      /** Format: date-time */
      readonly validated_at?: string | null;
    };
    PatchedMe: {
      readonly phone?: string;
      pseudo?: string;
      level?: components["schemas"]["LevelEnum"] | components["schemas"]["BlankEnum"];
      serie?: components["schemas"]["SerieEnum"] | components["schemas"]["BlankEnum"];
      /** Format: date-time */
      readonly date_joined?: string;
    };
    Progress: {
      summary: components["schemas"]["Summary"];
      subjects: components["schemas"]["SubjectProgress"][];
      chapters: components["schemas"]["Mastery"][];
      /** @description « Révision du jour » : 10 parcours au plus. */
      review_today: components["schemas"]["ReviewItem"][];
    };
    /**
     * @description * `to_finish` - to_finish
     *     * `to_review` - to_review
     * @enum {string}
     */
    ReasonEnum: "to_finish" | "to_review";
    /** @description Seule donnée personnelle collectée : le téléphone. `pseudo` est un nom d'affichage. */
    Register: {
      phone: string;
      pseudo: string;
      password: string;
      level: components["schemas"]["LevelEnum"];
      serie?: components["schemas"]["SerieEnum"] | components["schemas"]["BlankEnum"];
    };
    ReviewItem: {
      /**
       * @description to_finish : tentative commencée ; to_review : révision échue.
       *
       *     * `to_finish` - to_finish
       *     * `to_review` - to_review
       */
      reason: components["schemas"]["ReasonEnum"];
      exercise: components["schemas"]["Exercise"];
      /**
       * Format: uuid
       * @description Tentative à reprendre (to_finish).
       */
      attempt: string | null;
      /** Format: date-time */
      due_at: string;
      last_score: number | null;
    };
    /**
     * @description * `A` - A
     *     * `C` - C
     *     * `D` - D
     * @enum {string}
     */
    SerieEnum: "A" | "C" | "D";
    /**
     * @description * `non_acquis` - Non acquis
     *     * `en_cours` - En cours
     *     * `maitrise` - Maîtrisé
     * @enum {string}
     */
    StateEnum: "non_acquis" | "en_cours" | "maitrise";
    StepState: {
      step_id: string;
      status: components["schemas"]["StepStateStatusEnum"];
      wrong_answers: number;
      hints_used: number;
      /** @description Indices déjà obtenus (texte riche), du 1er au dernier : à réafficher à la reprise. */
      hints: string[];
      /** @description Sur 100 : 100 − 20 par indice − 20 par erreur ; 0 si échouée. */
      score: number;
    };
    /**
     * @description * `pending` - pending
     *     * `succeeded` - succeeded
     *     * `failed` - failed
     * @enum {string}
     */
    StepStateStatusEnum: "pending" | "succeeded" | "failed";
    Subject: {
      code: components["schemas"]["SubjectCodeEnum"];
      name: string;
    };
    /**
     * @description * `maths` - Mathématiques
     *     * `physique_chimie` - Physique-Chimie
     *     * `svt` - Sciences de la Vie et de la Terre
     *     * `francais` - Français
     *     * `anglais` - Anglais
     *     * `histoire_geo` - Histoire-Géographie
     * @enum {string}
     */
    SubjectCodeEnum: "maths" | "physique_chimie" | "svt" | "francais" | "anglais" | "histoire_geo";
    SubjectProgress: {
      subject: string;
      exercises_done: number;
      average_score: number;
    };
    Summary: {
      /** @description Parcours terminés au moins une fois. */
      exercises_done: number;
      attempts_finished: number;
      average_score: number | null;
      /** @description Jours consécutifs d'activité, jusqu'à aujourd'hui ou hier. */
      streak_days: number;
    };
    SyncAnswer: {
      step_id: string;
      /** @description Format selon le type d'activité (README §5.1). */
      response: unknown;
      /**
       * Format: uuid
       * @description Généré par le client : un renvoi ne crée pas de doublon.
       */
      client_uuid: string;
      /** Format: date-time */
      answered_at: string;
      /** @description Indices consultés hors-ligne pour cette étape. */
      hints_used?: number;
    };
    SyncAnswerResult: {
      /** Format: uuid */
      client_uuid: string;
      status: components["schemas"]["SyncAnswerResultStatusEnum"];
      is_correct: boolean | null;
      reason: string | null;
    };
    /**
     * @description * `accepted` - accepted
     *     * `duplicate` - duplicate
     *     * `rejected` - rejected
     * @enum {string}
     */
    SyncAnswerResultStatusEnum: "accepted" | "duplicate" | "rejected";
    SyncAttempt: {
      /** Format: uuid */
      id: string;
      /** Format: uuid */
      exercise: string;
      /** Format: date-time */
      started_at: string;
      answers: components["schemas"]["SyncAnswer"][];
    };
    SyncAttemptResult: {
      /** Format: uuid */
      id: string;
      status: components["schemas"]["SyncAttemptResultStatusEnum"];
      reason: string | null;
      attempt: components["schemas"]["Attempt"] | null;
      answers: components["schemas"]["SyncAnswerResult"][];
    };
    /**
     * @description * `synced` - synced
     *     * `rejected` - rejected
     * @enum {string}
     */
    SyncAttemptResultStatusEnum: "synced" | "rejected";
    SyncRequest: {
      attempts: components["schemas"]["SyncAttempt"][];
    };
    SyncResult: {
      attempts: components["schemas"]["SyncAttemptResult"][];
    };
    TokenRefreshRequest: {
      /** @description Mobile uniquement ; le web l'envoie par cookie httpOnly (body vide). */
      refresh?: string;
    };
    TokenRefreshResponse: {
      access: string;
      /** @description Nouveau refresh, seulement s'il a été envoyé dans le body (sinon : cookie). */
      refresh?: string;
    };
    Upload: {
      /** Format: uuid */
      readonly id: string;
      readonly file_type: components["schemas"]["FileTypeEnum"];
      readonly status: components["schemas"]["UploadStatusEnum"];
      readonly error_message: string;
      /** Format: date-time */
      readonly created_at: string;
      readonly exercises: components["schemas"]["ExtractedExercise"][];
    };
    UploadCreate: {
      /**
       * Format: binary
       * @description Photo (JPEG, PNG, WebP) ou PDF.
       */
      file: string;
    };
    /**
     * @description * `pending` - En attente
     *     * `reading` - Lecture en cours
     *     * `extracted` - Énoncés extraits
     *     * `error` - Erreur
     * @enum {string}
     */
    UploadStatusEnum: "pending" | "reading" | "extracted" | "error";
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  attempts_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) attempt. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Attempt"];
        };
      };
    };
  };
  attempts_answers_create: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) attempt. */
        id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["AnswerCreate"];
        "application/x-www-form-urlencoded": components["schemas"]["AnswerCreate"];
        "multipart/form-data": components["schemas"]["AnswerCreate"];
      };
    };
    responses: {
      /** @description Réponse déjà reçue (même client_uuid). */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnswerResult"];
        };
      };
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AnswerResult"];
        };
      };
      /** @description Réponse mal formée, étape non en cours, tentative terminée. */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  attempts_hints_create: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) attempt. */
        id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["HintRequest"];
        "application/x-www-form-urlencoded": components["schemas"]["HintRequest"];
        "multipart/form-data": components["schemas"]["HintRequest"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Hint"];
        };
      };
      /** @description Étape non en cours ou indices épuisés. */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  auth_login_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["Login"];
        "application/x-www-form-urlencoded": components["schemas"]["Login"];
        "multipart/form-data": components["schemas"]["Login"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["AccessToken"];
        };
      };
      /** @description Identifiants invalides. */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  auth_logout_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description No response body */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  auth_refresh_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: {
      content: {
        "application/json": components["schemas"]["TokenRefreshRequest"];
        "application/x-www-form-urlencoded": components["schemas"]["TokenRefreshRequest"];
        "multipart/form-data": components["schemas"]["TokenRefreshRequest"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["TokenRefreshResponse"];
        };
      };
      /** @description Refresh absent, expiré ou invalidé. */
      401: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  auth_register_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["Register"];
        "application/x-www-form-urlencoded": components["schemas"]["Register"];
        "multipart/form-data": components["schemas"]["Register"];
      };
    };
    responses: {
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Register"];
        };
      };
    };
  };
  curriculum_chapters_list: {
    parameters: {
      query?: {
        /** @description Niveau scolaire */
        level?: "1re" | "2nde" | "3e" | "4e" | "5e" | "6e" | "Tle";
        /** @description Code de la matière */
        subject?: "anglais" | "francais" | "histoire_geo" | "maths" | "physique_chimie" | "svt";
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Chapter"][];
        };
      };
    };
  };
  curriculum_chapters_retrieve: {
    parameters: {
      query?: {
        /** @description Niveau scolaire */
        level?: "1re" | "2nde" | "3e" | "4e" | "5e" | "6e" | "Tle";
        /** @description Code de la matière */
        subject?: "anglais" | "francais" | "histoire_geo" | "maths" | "physique_chimie" | "svt";
      };
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) chapter. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Chapter"];
        };
      };
    };
  };
  curriculum_subjects_list: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Subject"][];
        };
      };
    };
  };
  curriculum_subjects_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        code: "maths" | "physique_chimie" | "svt" | "francais" | "anglais" | "histoire_geo";
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Subject"];
        };
      };
    };
  };
  exercises_list: {
    parameters: {
      query?: {
        /** @description Uniquement les parcours de ce chapitre. */
        chapter?: string;
        /** @description La valeur du curseur de pagination. */
        cursor?: string;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["PaginatedExerciseList"];
        };
      };
    };
  };
  exercises_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExerciseDetail"];
        };
      };
    };
  };
  exercises_attempts_create: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: {
      content: {
        "application/json": components["schemas"]["AttemptStart"];
        "application/x-www-form-urlencoded": components["schemas"]["AttemptStart"];
        "multipart/form-data": components["schemas"]["AttemptStart"];
      };
    };
    responses: {
      /** @description Tentative déjà créée (même id). */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Attempt"];
        };
      };
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Attempt"];
        };
      };
      /** @description Parcours pas encore prêt. */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  exercises_events_retrieve: {
    parameters: {
      query?: {
        format?: "json" | "sse";
      };
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Flux SSE : un événement par statut (`pending`, `generating`, puis `ready`, `needs_review` ou `error`, qui terminent le flux), `data` = le parcours comme dans `GET /api/exercises/{id}/` (l'événement `ready` contient donc le contenu). */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "text/event-stream": string;
        };
      };
    };
  };
  exercises_offline_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExerciseOffline"];
        };
      };
    };
  };
  extracted_exercises_destroy: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) extracted exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description No response body */
      204: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  extracted_exercises_partial_update: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) extracted exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: {
      content: {
        "application/json": components["schemas"]["PatchedExtractedExercise"];
        "application/x-www-form-urlencoded": components["schemas"]["PatchedExtractedExercise"];
        "multipart/form-data": components["schemas"]["PatchedExtractedExercise"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExtractedExercise"];
        };
      };
    };
  };
  extracted_exercises_generate_create: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) extracted exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Parcours existant ou repris du cache. */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Exercise"];
        };
      };
      /** @description Génération lancée : suivre generation_status. */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Exercise"];
        };
      };
      /** @description Énoncé non validé ou matière non ouverte. */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Quota journalier atteint (en-tête Retry-After). */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  extracted_exercises_validate_create: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) extracted exercise. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["ExtractedExercise"];
        };
      };
      /** @description Matière ou niveau manquant. */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  me_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Me"];
        };
      };
    };
  };
  me_partial_update: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: {
      content: {
        "application/json": components["schemas"]["PatchedMe"];
        "application/x-www-form-urlencoded": components["schemas"]["PatchedMe"];
        "multipart/form-data": components["schemas"]["PatchedMe"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Me"];
        };
      };
    };
  };
  progress_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Progress"];
        };
      };
    };
  };
  sync_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "application/json": components["schemas"]["SyncRequest"];
        "application/x-www-form-urlencoded": components["schemas"]["SyncRequest"];
        "multipart/form-data": components["schemas"]["SyncRequest"];
      };
    };
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["SyncResult"];
        };
      };
    };
  };
  uploads_create: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        "multipart/form-data": components["schemas"]["UploadCreate"];
      };
    };
    responses: {
      /** @description Document déjà envoyé : upload existant. */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Upload"];
        };
      };
      201: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Upload"];
        };
      };
      /** @description Fichier refusé (type, taille, pages). */
      400: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
      /** @description Quota journalier atteint (en-tête Retry-After). */
      429: {
        headers: {
          [name: string]: unknown;
        };
        content?: never;
      };
    };
  };
  uploads_retrieve: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) upload. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "application/json": components["schemas"]["Upload"];
        };
      };
    };
  };
  uploads_events_retrieve: {
    parameters: {
      query?: {
        format?: "json" | "sse";
      };
      header?: never;
      path: {
        /** @description Un(une) Chaîne UUID identifiant ce(cette) upload. */
        id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Flux SSE : un événement par statut (`pending`, `reading`, puis `extracted` ou `error`, qui terminent le flux), `data` = l'upload comme dans `GET /api/uploads/{id}/`. */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          "text/event-stream": string;
        };
      };
    };
  };
}
