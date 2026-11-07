import { exerciseContent, toPublic } from "@stem/content-schema/fixtures";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { json, mockApi, renderApp, sse } from "@/test-utils";

const ME = {
  phone: "061234567",
  pseudo: "kiki",
  level: "1re",
  serie: "C",
  date_joined: "2026-11-07T10:00:00Z",
};

const extracted = (overrides: Record<string, unknown> = {}) => ({
  id: "ex1",
  order: 1,
  statement: "Étudier les variations de $f(x) = x^2 - 4x + 3$.",
  subject: "maths",
  chapter: null,
  chapter_hint: "Dérivation",
  level: "1re",
  validated_at: null,
  ...overrides,
});

const upload = (status: string, exercises: unknown[] = []) => ({
  id: "up1",
  file_type: "image",
  status,
  error_message: "",
  created_at: "2026-11-07T10:00:00Z",
  exercises,
});

const exercise = (generation_status: string, extra: Record<string, unknown> = {}) => ({
  id: "pa1",
  title: generation_status === "ready" ? "Variations d'une fonction du second degré" : "",
  subject: "maths",
  chapter: null,
  level: "1re",
  exam: "BAC",
  generation_status,
  error_message: "",
  created_at: "2026-11-07T10:00:00Z",
  ...extra,
});

const path = (request: Request) => new URL(request.url).pathname;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("scanner : envoi", () => {
  it("envoie un PDF tel quel puis suit sa lecture", async () => {
    const calls = mockApi((request) => {
      if (path(request) === "/api/uploads/" && request.method === "POST") return json(201, upload("pending"));
      if (path(request) === "/api/uploads/up1/") return json(200, upload("pending"));
      if (path(request) === "/api/uploads/up1/events/") return sse([["reading", upload("reading")]]);
      return undefined;
    });
    const router = renderApp("/scanner", { authenticated: true });

    const pdf = new File(["%PDF-1.4"], "fiche.pdf", { type: "application/pdf" });
    await userEvent.upload(await screen.findByLabelText("Importer une photo ou un PDF"), pdf);
    expect(screen.getByText("PDF prêt à envoyer : fiche.pdf")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/scanner/up1"));
    expect(await screen.findByText("Je lis ton document…")).toBeInTheDocument();
    const sent = calls.find((c) => c.path === "/api/uploads/" && c.method === "POST")?.body as FormData;
    expect((sent.get("file") as File).name).toBe("fiche.pdf");
  });

  it("refuse un format non pris en charge sans rien envoyer", async () => {
    const calls = mockApi(() => undefined);
    renderApp("/scanner", { authenticated: true });
    const doc = new File(["x"], "notes.docx", { type: "application/msword" });
    await userEvent.upload(await screen.findByLabelText("Importer une photo ou un PDF"), doc, {
      applyAccept: false,
    });
    expect(await screen.findByText(/Format non pris en charge/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("affiche le quota atteint avec l'heure de reprise", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-07T20:00:00Z"));
    mockApi((request) =>
      path(request) === "/api/uploads/"
        ? new Response(
            JSON.stringify({ detail: "Tu as atteint le nombre de documents autorisés aujourd'hui." }),
            {
              status: 429,
              headers: { "Content-Type": "application/json", "Retry-After": "3600" },
            },
          )
        : undefined,
    );
    renderApp("/scanner", { authenticated: true });
    await userEvent.upload(
      await screen.findByLabelText("Importer une photo ou un PDF"),
      new File(["%PDF"], "a.pdf", { type: "application/pdf" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Envoyer" }));
    // 21h00 UTC = 22h00 à Brazzaville.
    expect(
      await screen.findByText(/aujourd'hui\. Tu pourras réessayer à partir de 22h00\./),
    ).toBeInTheDocument();
    vi.useRealTimers();
  });
});

describe("scanner : vérification de l'énoncé", () => {
  it("passe de la lecture aux exercices trouvés en direct (SSE)", async () => {
    const calls = mockApi((request) => {
      if (path(request) === "/api/me/") return json(200, ME);
      if (path(request) === "/api/uploads/up1/") return json(200, upload("reading"));
      if (path(request) === "/api/uploads/up1/events/")
        return sse([
          ["reading", upload("reading")],
          [
            "extracted",
            upload("extracted", [
              extracted(),
              extracted({ id: "ex2", order: 2, statement: "Résoudre $x^2 = 4$." }),
            ]),
          ],
        ]);
      return undefined;
    });
    renderApp("/scanner/up1", { authenticated: true });

    expect(await screen.findByRole("heading", { name: "2 exercices trouvés" })).toBeInTheDocument();
    // Le flux ne part qu'après le premier GET, et s'arrête sur `extracted`.
    expect(calls.map((c) => c.path).filter((p) => p.startsWith("/api/uploads/"))).toEqual([
      "/api/uploads/up1/",
      "/api/uploads/up1/events/",
    ]);
    expect(screen.getByRole("tab", { name: "Exercice 1" })).toHaveAttribute("aria-selected", "true");
    await userEvent.click(screen.getByRole("tab", { name: "Exercice 2" }));
    expect(screen.getByLabelText("Énoncé")).toHaveValue("Résoudre $x^2 = 4$.");
  });

  it("envoie la correction, valide, lance la génération puis ouvre la préparation", async () => {
    const calls = mockApi((request) => {
      const p = path(request);
      if (p === "/api/me/") return json(200, ME);
      if (p === "/api/curriculum/chapters/") return json(200, []);
      if (p === "/api/uploads/up1/") return json(200, upload("extracted", [extracted()]));
      if (p === "/api/extracted-exercises/ex1/" && request.method === "PATCH")
        return json(200, extracted({ statement: "Étudier $f(x) = x^2 - 4x + 5$." }));
      if (p === "/api/extracted-exercises/ex1/validate/")
        return json(200, extracted({ validated_at: "2026-11-07T10:01:00Z" }));
      if (p === "/api/extracted-exercises/ex1/generate/") return json(202, exercise("pending"));
      if (p === "/api/exercises/pa1/")
        return json(200, { ...exercise("pending"), schema_version: "1.1", content: null });
      if (p === "/api/exercises/pa1/events/")
        return sse([["generating", { ...exercise("generating"), content: null }]]);
      return undefined;
    });
    const router = renderApp("/scanner/up1", { authenticated: true });

    const statement = await screen.findByLabelText("Énoncé");
    expect(screen.getByText("Lu sur la feuille : « Dérivation »")).toBeInTheDocument();
    await userEvent.clear(statement);
    await userEvent.type(statement, "Étudier $f(x) = x^2 - 4x + 5$.");
    await userEvent.click(screen.getByRole("button", { name: "C'est bon, on y va" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/parcours/pa1"));
    expect(router.state.location.search).toBe("?enonce=ex1");
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({
      statement: "Étudier $f(x) = x^2 - 4x + 5$.",
    });
    expect(calls.map((c) => c.path)).toEqual(
      expect.arrayContaining([
        "/api/extracted-exercises/ex1/validate/",
        "/api/extracted-exercises/ex1/generate/",
      ]),
    );
    expect(await screen.findByText("Je prépare ton parcours…")).toBeInTheDocument();
  });

  it("affiche sous le champ l'erreur de l'API sur l'énoncé", async () => {
    mockApi((request) => {
      const p = path(request);
      if (p === "/api/me/") return json(200, ME);
      if (p === "/api/uploads/up1/") return json(200, upload("extracted", [extracted()]));
      if (p === "/api/extracted-exercises/ex1/")
        return json(400, { statement: ["Le HTML n'est pas autorisé."] });
      return json(200, []);
    });
    renderApp("/scanner/up1", { authenticated: true });
    const statement = await screen.findByLabelText("Énoncé");
    await userEvent.type(statement, " <b>");
    await userEvent.click(screen.getByRole("button", { name: "C'est bon, on y va" }));
    expect(await screen.findByText("Le HTML n'est pas autorisé.")).toBeInTheDocument();
    expect(statement).toHaveAttribute("aria-invalid", "true");
  });

  it("bloque une matière pas encore ouverte", async () => {
    mockApi((request) => {
      if (path(request) === "/api/me/") return json(200, ME);
      if (path(request) === "/api/uploads/up1/")
        return json(200, upload("extracted", [extracted({ subject: "svt" })]));
      return json(200, []);
    });
    renderApp("/scanner/up1", { authenticated: true });
    expect(await screen.findByText(/Cette matière n'est pas encore disponible/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "C'est bon, on y va" })).toBeDisabled();
  });

  it("écarte un exercice après confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const calls = mockApi((request) => {
      if (path(request) === "/api/me/") return json(200, ME);
      if (path(request) === "/api/uploads/up1/") return json(200, upload("extracted", [extracted()]));
      if (request.method === "DELETE") return new Response(null, { status: 204 });
      return json(200, []);
    });
    renderApp("/scanner/up1", { authenticated: true });
    await userEvent.click(await screen.findByRole("button", { name: "Écarter" }));
    expect(await screen.findByText("Je n'ai trouvé aucun exercice sur ce document.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/api/extracted-exercises/ex1/")).toBe(true);
  });

  it("explique un échec de lecture", async () => {
    mockApi((request) =>
      path(request) === "/api/uploads/up1/"
        ? json(200, { ...upload("error"), error_message: "Photo trop floue." })
        : undefined,
    );
    renderApp("/scanner/up1", { authenticated: true });
    expect(await screen.findByText("Photo trop floue.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Essayer avec une autre photo" })).toHaveAttribute(
      "href",
      "/scanner",
    );
  });
});

describe("parcours : préparation", () => {
  it("affiche le parcours prêt avec son nombre d'étapes", async () => {
    const content = toPublic(exerciseContent());
    mockApi((request) =>
      path(request) === "/api/exercises/pa1/"
        ? json(200, { ...exercise("ready"), schema_version: "1.1", content })
        : undefined,
    );
    renderApp("/parcours/pa1", { authenticated: true });
    expect(
      await screen.findByRole("heading", { name: "Variations d'une fonction du second degré" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2 étapes")).toBeInTheDocument();
  });

  it("relance une préparation échouée et reprend le suivi", async () => {
    let status = "error";
    const calls = mockApi((request) => {
      const p = path(request);
      if (p === "/api/exercises/pa1/")
        return json(200, {
          ...exercise(status, { error_message: "La préparation a pris trop de temps." }),
          schema_version: "1.1",
          content: null,
        });
      if (p === "/api/extracted-exercises/ex1/generate/") {
        status = "pending";
        return json(202, exercise("pending"));
      }
      if (p === "/api/exercises/pa1/events/")
        return sse([["generating", { ...exercise("generating"), content: null }]]);
      return undefined;
    });
    renderApp("/parcours/pa1?enonce=ex1", { authenticated: true });

    const alert = await screen.findByText("La préparation a pris trop de temps.");
    expect(alert).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Relancer la préparation" }));
    const status_ = await screen.findByRole("status");
    expect(within(status_).getByText("Je prépare ton parcours…")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/extracted-exercises/ex1/generate/")).toBe(true);
  });
});
