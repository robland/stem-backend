import { getAccessToken, getSessionStatus, setAccessToken } from "./auth";
import { configureApi, getApi, restoreSession, unwrap } from "./client";
import { ApiError, parseRetryAfter } from "./errors";

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });

type Handler = (request: Request) => Response;

function mockFetch(handler: Handler) {
  const calls: Request[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request) => {
      calls.push(input.clone());
      return handler(input);
    }),
  );
  return calls;
}

const path = (request: Request) => new URL(request.url).pathname;

beforeEach(() => {
  configureApi({ baseUrl: "http://api.test" });
  setAccessToken(null);
});

afterEach(() => vi.unstubAllGlobals());

describe("authFetch", () => {
  it("ajoute le jeton d'accès", async () => {
    setAccessToken("A1");
    const calls = mockFetch(() => json(200, { pseudo: "kiki" }));
    await getApi().GET("/api/me/");
    expect(calls[0]?.headers.get("Authorization")).toBe("Bearer A1");
  });

  it("rafraîchit le jeton sur 401 puis rejoue la requête avec son corps", async () => {
    setAccessToken("expire");
    const calls = mockFetch((request) => {
      if (path(request) === "/api/auth/refresh/") return json(200, { access: "A2" });
      return request.headers.get("Authorization") === "Bearer A2" ? json(200, { pseudo: "neo" }) : json(401, {});
    });

    const me = await unwrap(getApi().PATCH("/api/me/", { body: { pseudo: "neo" } }));

    expect(me).toEqual({ pseudo: "neo" });
    expect(getAccessToken()).toBe("A2");
    expect(calls.map(path)).toEqual(["/api/me/", "/api/auth/refresh/", "/api/me/"]);
    expect(await calls[2]?.json()).toEqual({ pseudo: "neo" });
  });

  it("un seul refresh pour des 401 simultanés", async () => {
    setAccessToken("expire");
    const calls = mockFetch((request) => {
      if (path(request) === "/api/auth/refresh/") return json(200, { access: "A2" });
      return request.headers.get("Authorization") === "Bearer A2" ? json(200, {}) : json(401, {});
    });

    await Promise.all([getApi().GET("/api/me/"), getApi().GET("/api/progress/")]);

    expect(calls.filter((c) => path(c) === "/api/auth/refresh/")).toHaveLength(1);
  });

  it("refresh refusé : session anonyme, réponse 401 renvoyée", async () => {
    setAccessToken("expire");
    mockFetch(() => json(401, { detail: "Jeton invalide" }));

    await expect(unwrap(getApi().GET("/api/me/"))).rejects.toMatchObject({ status: 401 });
    expect(getSessionStatus()).toBe("anonymous");
  });

  it("pas de refresh sur un échec de connexion", async () => {
    const calls = mockFetch(() => json(401, { detail: "Identifiants invalides" }));
    await getApi().POST("/api/auth/login/", { body: { phone: "1", password: "x" } as never });
    expect(calls.map(path)).toEqual(["/api/auth/login/"]);
  });
});

describe("restoreSession", () => {
  it("restaure la session depuis le cookie de refresh", async () => {
    mockFetch(() => json(200, { access: "A3" }));
    expect(await restoreSession()).toBe(true);
    expect(getSessionStatus()).toBe("authenticated");
  });

  it("sans cookie : anonyme", async () => {
    mockFetch(() => json(401, { detail: "Aucun refresh token fourni." }));
    expect(await restoreSession()).toBe(false);
    expect(getSessionStatus()).toBe("anonymous");
  });
});

describe("ApiError", () => {
  it("expose les erreurs par champ et Retry-After", async () => {
    mockFetch(() => json(429, { detail: "Quota atteint" }, { "Retry-After": "60" }));
    const error = await unwrap(getApi().GET("/api/progress/")).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).detail).toBe("Quota atteint");
    expect((error as ApiError).retryAfter).toBeInstanceOf(Date);
  });

  it("lit les erreurs DRF par champ", () => {
    const error = new ApiError(400, { phone: ["Numéro déjà utilisé."], pseudo: "Trop long" });
    expect(error.fieldErrors).toEqual({ phone: "Numéro déjà utilisé.", pseudo: "Trop long" });
  });

  it("parseRetryAfter accepte secondes et date HTTP", () => {
    expect(parseRetryAfter("10", 0)?.getTime()).toBe(10_000);
    expect(parseRetryAfter("Wed, 21 Oct 2026 07:28:00 GMT")?.toISOString()).toBe("2026-10-21T07:28:00.000Z");
    expect(parseRetryAfter(null)).toBeNull();
  });
});
