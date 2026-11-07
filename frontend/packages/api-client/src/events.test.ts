import { setAccessToken } from "./auth";
import { configureApi } from "./client";
import { EventsUnavailable, followEvents } from "./events";

const encoder = new TextEncoder();

/** Réponse SSE dont le corps émet `chunks` puis se ferme. */
function sse(chunks: string[], status = 200) {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
  return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
}

const event = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

function mockFetch(responses: (() => Response)[]) {
  const calls: Request[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      calls.push(request);
      const next = responses.shift();
      if (!next) throw new Error("plus de réponse prévue");
      return next();
    }),
  );
  return calls;
}

beforeEach(() => {
  configureApi({ baseUrl: "http://api.test" });
  setAccessToken("A1");
});
afterEach(() => vi.unstubAllGlobals());

describe("followEvents", () => {
  it("transmet chaque statut et s'arrête sur un statut final", async () => {
    const calls = mockFetch([
      () =>
        sse([
          "retry: 2000\n\n",
          event("pending", { status: "pending" }),
          ": ping\n\n",
          event("reading", { status: "reading" }),
          event("extracted", { status: "extracted" }),
        ]),
    ]);
    const updates: string[] = [];

    await followEvents("/api/uploads/u1/events/", {
      terminal: ["extracted", "error"],
      onUpdate: (s) => updates.push(s),
    });

    expect(updates).toEqual(["pending", "reading", "extracted"]);
    expect(calls[0]?.headers.get("Authorization")).toBe("Bearer A1");
    expect(calls[0]?.headers.get("Accept")).toBe("text/event-stream");
  });

  it("se reconnecte quand le serveur ferme le flux avant la fin", async () => {
    const calls = mockFetch([
      () => sse([event("generating", { s: 1 })]),
      () => sse([event("generating", { s: 1 }), event("ready", { s: 2 })]),
    ]);
    const updates: string[] = [];

    await followEvents("/api/exercises/e1/events/", {
      terminal: ["ready"],
      onUpdate: (s) => updates.push(s),
      retryMs: 1,
    });

    expect(calls).toHaveLength(2);
    expect(updates).toEqual(["generating", "generating", "ready"]);
  });

  it("signale un serveur sans SSE (repli en polling)", async () => {
    mockFetch([() => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } })]);
    await expect(followEvents("/x/", { terminal: [], onUpdate: () => {} })).rejects.toBeInstanceOf(
      EventsUnavailable,
    );
  });

  it("signale un objet disparu", async () => {
    mockFetch([() => sse([event("gone", { detail: "Introuvable." })])]);
    await expect(followEvents("/x/", { terminal: [], onUpdate: () => {} })).rejects.toMatchObject({
      reason: "gone",
    });
  });

  it("s'arrête sans erreur quand l'appelant annule", async () => {
    const controller = new AbortController();
    mockFetch([
      () => {
        controller.abort();
        return sse([]);
      },
    ]);
    await expect(
      followEvents("/x/", { terminal: [], onUpdate: () => {}, signal: controller.signal }),
    ).resolves.toBeUndefined();
  });
});
