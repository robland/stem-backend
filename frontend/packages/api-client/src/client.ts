import createClient, { type Client } from "openapi-fetch";
import { getAccessToken, refreshAccessToken, setAccessToken, setRefresher } from "./auth";
import { ApiError, parseRetryAfter } from "./errors";
import type { paths } from "./generated/schema.gen";

export type ApiClient = Client<paths>;

// Routes où un 401 signifie « identifiants refusés », pas « jeton expiré ».
const NO_REFRESH = ["/api/auth/login/", "/api/auth/refresh/", "/api/auth/register/", "/api/auth/logout/"];

let baseUrl = "";
let client: ApiClient;
// Client sans relance sur 401, pour le rafraîchissement lui-même.
let authClient: ApiClient;

function withAuth(request: Request): Request {
  const authed = new Request(request, { credentials: "include" });
  const token = getAccessToken();
  if (token) authed.headers.set("Authorization", `Bearer ${token}`);
  return authed;
}

/** fetch authentifié : ajoute le Bearer, rafraîchit le jeton sur 401 puis rejoue la requête une fois. */
export async function authFetch(request: Request): Promise<Response> {
  const replay = request.clone();
  const response = await fetch(withAuth(request));
  const path = new URL(request.url, "http://x").pathname;
  if (response.status !== 401 || NO_REFRESH.includes(path)) return response;
  const token = await refreshAccessToken();
  return token ? fetch(withAuth(replay)) : response;
}

export function configureApi(options: { baseUrl?: string } = {}) {
  baseUrl = options.baseUrl ?? "";
  client = createClient<paths>({ baseUrl, fetch: authFetch });
  // `fetch` résolu à l'appel (et non capturé à la création) : remplaçable dans les tests.
  authClient = createClient<paths>({ baseUrl, credentials: "include", fetch: (request) => fetch(request) });
  setRefresher(async () => {
    // Web : body vide, le refresh est lu dans le cookie httpOnly.
    const { data } = await authClient.POST("/api/auth/refresh/", { body: {} });
    return data?.access ?? null;
  });
}

configureApi();

export const getApi = () => client;
export const getAuthApi = () => authClient;
export const getBaseUrl = () => baseUrl;

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/** Convertit le résultat d'openapi-fetch en valeur ou en `ApiError` (pour TanStack Query). */
export async function unwrap<T>(promise: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await promise;
  if (!response.ok) {
    throw new ApiError(response.status, error ?? null, parseRetryAfter(response.headers.get("Retry-After")));
  }
  return data as T;
}

/** Restaure la session au chargement (cookie de refresh encore valide ?). */
export async function restoreSession(): Promise<boolean> {
  return (await refreshAccessToken()) !== null;
}

export async function logout() {
  try {
    await authClient.POST("/api/auth/logout/");
  } finally {
    setAccessToken(null);
  }
}
