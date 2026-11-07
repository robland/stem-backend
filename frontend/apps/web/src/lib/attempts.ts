// Tentative en cours par parcours, mémorisée sur l'appareil pour reprendre où l'élève s'était arrêté
// (commodité locale ; la tentative elle-même vit sur le serveur).
const key = (exerciseId: string) => `stem.attempt.${exerciseId}`;

export function rememberedAttempt(exerciseId: string): string | null {
  try {
    return localStorage.getItem(key(exerciseId));
  } catch {
    return null;
  }
}

export function rememberAttempt(exerciseId: string, attemptId: string) {
  try {
    localStorage.setItem(key(exerciseId), attemptId);
  } catch {
    /* stockage indisponible : pas de reprise après rechargement */
  }
}

export const newId = () => crypto.randomUUID();
