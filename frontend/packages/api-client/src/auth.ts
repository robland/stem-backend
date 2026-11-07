// Jeton d'accès en mémoire uniquement (jamais en localStorage) ; le refresh vit dans un cookie httpOnly
// posé par l'API (web), cf. README frontend §6.

export type SessionStatus = "unknown" | "authenticated" | "anonymous";

type Listener = () => void;

let accessToken: string | null = null;
let status: SessionStatus = "unknown";
const listeners = new Set<Listener>();

export const getAccessToken = () => accessToken;
export const getSessionStatus = () => status;

export function setAccessToken(token: string | null) {
  accessToken = token;
  status = token ? "authenticated" : "anonymous";
  listeners.forEach((listener) => listener());
}

export function subscribeSession(listener: Listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

type Refresher = () => Promise<string | null>;
let refresher: Refresher = async () => null;
let inFlight: Promise<string | null> | null = null;

export function setRefresher(fn: Refresher) {
  refresher = fn;
}

/** Un seul rafraîchissement à la fois : les requêtes en 401 simultanées attendent le même. */
export function refreshAccessToken(): Promise<string | null> {
  inFlight ??= refresher()
    .catch(() => null)
    .then((token) => {
      setAccessToken(token);
      return token;
    })
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}
