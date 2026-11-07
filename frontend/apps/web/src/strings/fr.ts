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
    streak: (days: number) => (days > 1 ? `${days} jours d'affilée` : days === 1 ? "1 jour d'affilée" : "Commence ta série aujourd'hui"),
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
