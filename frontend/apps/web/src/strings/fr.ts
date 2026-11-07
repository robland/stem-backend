// Tous les textes d'interface (README frontend §8.2). Le contenu pédagogique vient de l'API.
import type { Level, SubjectCode } from "@stem/api-client";

export const APP_NAME = "StemLearning";

export const LEVELS: { value: Level; label: string }[] = [
  { value: "6e", label: "6e" },
  { value: "5e", label: "5e" },
  { value: "4e", label: "4e" },
  { value: "3e", label: "3e" },
  { value: "2nde", label: "2nde" },
  { value: "1re", label: "1re" },
  { value: "Tle", label: "Terminale" },
];

export const HIGH_SCHOOL_LEVELS: Level[] = ["2nde", "1re", "Tle"];

// L'API accepte une série libre (≤ 10 caractères) : liste à confirmer avec le porteur du projet.
export const SERIES = ["A", "C", "D"] as const;

export const SUBJECTS: { value: SubjectCode; label: string; available: boolean }[] = [
  { value: "maths", label: "Mathématiques", available: true },
  { value: "physique_chimie", label: "Physique-Chimie", available: true },
  { value: "svt", label: "SVT", available: false },
  { value: "francais", label: "Français", available: false },
  { value: "anglais", label: "Anglais", available: false },
  { value: "histoire_geo", label: "Histoire-Géo", available: false },
];

export type Goal = "devoirs" | "bepc" | "bac";

export const t = {
  common: {
    next: "Continuer",
    back: "Retour",
    save: "Enregistrer",
    saved: "Enregistré",
    loading: "Chargement…",
    retry: "Réessayer",
    soon: "Bientôt disponible",
    networkError: "Connexion impossible. Vérifie ton réseau puis réessaie.",
    unknownError: "Une erreur est survenue. Réessaie dans un instant.",
    optional: "facultatif",
  },
  nav: {
    home: "Accueil",
    challenges: "Défis",
    scan: "Scanner",
    progress: "Progrès",
    profile: "Profil",
    main: "Navigation principale",
  },
  auth: {
    loginTitle: "Content de te revoir",
    loginSubtitle: "Connecte-toi avec ton numéro de téléphone.",
    phone: "Numéro de téléphone",
    phoneHint: "Ex. 06 123 45 67",
    password: "Mot de passe",
    showPassword: "Afficher le mot de passe",
    hidePassword: "Masquer le mot de passe",
    login: "Se connecter",
    noAccount: "Pas encore de compte ?",
    createAccount: "Créer un compte",
    hasAccount: "Déjà un compte ?",
    invalidCredentials: "Numéro ou mot de passe incorrect.",
    phoneInvalid: "Entre un numéro de 8 à 15 chiffres.",
    passwordRequired: "Entre ton mot de passe.",
  },
  register: {
    steps: ["Ton compte", "Ta classe", "Tes matières", "Ton objectif"],
    stepLabel: (n: number, total: number) => `Étape ${n} sur ${total}`,
    accountTitle: "Crée ton compte",
    accountSubtitle: "Ton numéro sert uniquement à te connecter. Les autres élèves ne voient que ton pseudo.",
    pseudo: "Pseudo",
    pseudoHint: "Visible par les autres élèves. Évite ton vrai nom.",
    pseudoRequired: "Choisis un pseudo.",
    pseudoTooLong: "30 caractères maximum.",
    passwordHint: "8 caractères minimum, pas uniquement des chiffres.",
    passwordTooShort: "8 caractères minimum.",
    levelTitle: "En quelle classe es-tu ?",
    level: "Ta classe",
    levelRequired: "Choisis ta classe.",
    serie: "Ta série",
    serieRequired: "Choisis ta série.",
    subjectsTitle: "Quelles matières veux-tu travailler ?",
    subjects: "Matières",
    subjectsSoon: "Les autres matières arrivent bientôt.",
    goalTitle: "Quel est ton objectif ?",
    goal: "Objectif",
    goals: {
      devoirs: { label: "Mes devoirs", description: "Comprendre les exercices de la semaine" },
      bepc: { label: "Le BEPC", description: "Réviser pour l'examen de 3e" },
      bac: { label: "Le BAC", description: "Réviser pour l'examen de Terminale" },
    } satisfies Record<Goal, { label: string; description: string }>,
    submit: "Créer mon compte",
    finish: "C'est parti !",
    accountCreatedLoginFailed: "Compte créé. Connecte-toi pour continuer.",
  },
  home: {
    hello: (pseudo: string) => `Salut ${pseudo} !`,
    scanCta: "Photographie ton exercice",
    scanCtaHint: "On le résout ensemble, étape par étape.",
    reviewToday: "Révision du jour",
    reviewEmpty: "Rien à réviser aujourd'hui. Scanne un nouvel exercice !",
    toFinish: "À terminer",
    toReview: "À revoir",
    streak: (days: number) =>
      days > 1
        ? `${days} jours d'affilée`
        : days === 1
          ? "1 jour d'affilée"
          : "Commence ta série aujourd'hui",
  },
  progress: {
    title: "Mes progrès",
  },
  challenges: {
    title: "Défis",
    soon: "Lance des défis à tes camarades avec les exercices que tu as travaillés. Bientôt disponible !",
  },
  scan: {
    title: "Scanner un exercice",
    subtitle: "Prends ton exercice en photo, ou importe une photo ou un PDF.",
    takePhoto: "Prendre une photo",
    importFile: "Importer une photo ou un PDF",
    tips: [
      "Feuille bien à plat, avec de la lumière",
      "Tout l'exercice dans le cadre",
      "Évite ton nom : recadre-le si possible",
    ],
    cropTitle: "Recadre ton exercice",
    cropHint: "Garde seulement l'énoncé : la photo sera plus légère et mieux lue.",
    cropAlt: "Ta photo à recadrer",
    cropMove: "Déplacer le cadre (flèches du clavier)",
    cropCorners: {
      nw: "Coin haut gauche (flèches du clavier)",
      ne: "Coin haut droit (flèches du clavier)",
      sw: "Coin bas gauche (flèches du clavier)",
      se: "Coin bas droit (flèches du clavier)",
    },
    rotate: "Tourner",
    retake: "Changer de photo",
    send: "Envoyer",
    sending: "Envoi…",
    pdfReady: (name: string) => `PDF prêt à envoyer : ${name}`,
    unsupported: "Format non pris en charge : choisis une photo (JPEG, PNG, WebP) ou un PDF.",
    tooBig: "Fichier trop lourd : 10 Mo maximum.",
    imageError: "Impossible de lire cette image. Essaie avec une autre photo.",
    quota: (detail: string, at: string | null) =>
      at ? `${detail} Tu pourras réessayer à partir de ${at}.` : detail,
    reading: "Je lis ton document…",
    readingHint: "Ça prend quelques secondes. Garde cette page ouverte.",
    readError: "Je n'ai pas pu lire ce document.",
    retry: "Essayer avec une autre photo",
    noneFound: "Je n'ai trouvé aucun exercice sur ce document.",
    found: (n: number) => (n > 1 ? `${n} exercices trouvés` : "1 exercice trouvé"),
    exercisesTabs: "Exercices trouvés",
    exerciseTab: (n: number) => `Exercice ${n}`,
    yourPhoto: "Ta photo (reste sur ton appareil)",
    checkTitle: "Vérifie ce que j'ai lu",
    checkHint: "Corrige si un chiffre ou un signe est faux : le parcours partira de ce texte.",
    statement: "Énoncé",
    statementHint: "Formules entre $ … $, par exemple $x^2 - 4x + 3$.",
    preview: "Aperçu",
    subject: "Matière",
    subjectMissing: "Choisis la matière.",
    subjectSoon: (label: string) => `${label} (bientôt)`,
    subjectNotOpen:
      "Cette matière n'est pas encore disponible : seuls les Maths et la Physique-Chimie le sont.",
    level: "Classe",
    levelMissing: "Choisis la classe.",
    chapter: "Chapitre",
    chapterNone: "Je ne sais pas",
    chapterHint: (hint: string) => `Lu sur la feuille : « ${hint} »`,
    discard: "Écarter",
    discardConfirm: "Écarter cet exercice ? Tu ne pourras pas le récupérer.",
    go: "C'est bon, on y va",
    open: "Ouvrir le parcours",
    validated: "Énoncé validé : il ne peut plus être modifié.",
    allDiscarded: "Tous les exercices ont été écartés.",
    newScan: "Scanner un autre exercice",
  },
  exercise: {
    preparing: "Je prépare ton parcours…",
    preparingHint: "Ça prend environ une minute. Tu peux quitter cet écran, ton parcours t'attendra.",
    stepsLabel: "Avancement",
    // L'API ne distingue pas découpage et vérification (un seul statut `generating`).
    steps: { read: "Énoncé lu et vérifié", build: "Découpage en étapes et vérification des calculs" },
    promise:
      "Je ne te donnerai pas la réponse : tu vas la trouver toi-même, une étape à la fois. Les indices sont là si tu bloques.",
    ready: "Ton parcours est prêt !",
    readerSoon: "Le lecteur de parcours arrive à la prochaine étape du développement.",
    stepsCount: (n: number) => (n > 1 ? `${n} étapes` : "1 étape"),
    needsReview: "Ce parcours doit être relu avant de t'être proposé. Réessaie un peu plus tard.",
    error: "La préparation a échoué.",
    relaunch: "Relancer la préparation",
    backHome: "Revenir à l'accueil",
  },
  profile: {
    title: "Mon profil",
    account: "Mon compte",
    phone: "Téléphone",
    preferences: "Préférences",
    theme: "Apparence",
    themes: { system: "Automatique", light: "Clair", dark: "Sombre" },
    dyslexicFont: "Police adaptée à la dyslexie",
    dyslexicFontHint: "Téléchargée uniquement si tu l'actives.",
    logout: "Se déconnecter",
  },
  notFound: "Cette page n'existe pas.",
  backHome: "Retour à l'accueil",
};
