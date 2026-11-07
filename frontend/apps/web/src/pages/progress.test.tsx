import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { json, mockApi, renderApp } from "@/test-utils";

const chapter = (id: string, name: string, subject = "maths") => ({
  id,
  subject,
  level: "1re",
  name,
  order: 1,
});
const exercise = (id: string, title: string, status = "ready") => ({
  id,
  title,
  subject: "maths",
  chapter: null,
  level: "1re",
  exam: "BAC",
  generation_status: status,
  error_message: "",
  created_at: "2026-11-07T10:00:00Z",
});

const PROGRESS = {
  summary: { exercises_done: 12, attempts_finished: 15, average_score: 71, streak_days: 4 },
  subjects: [
    { subject: "maths", exercises_done: 9, average_score: 74 },
    { subject: "physique_chimie", exercises_done: 3, average_score: 62 },
  ],
  chapters: [
    {
      chapter: chapter("c1", "Calcul littéral"),
      score: 88,
      state: "maitrise",
      next_review_at: null,
      updated_at: "2026-11-07T10:00:00Z",
    },
    {
      chapter: chapter("c2", "Dérivation"),
      score: 58,
      state: "en_cours",
      next_review_at: "2026-11-08T10:00:00Z",
      updated_at: "2026-11-07T10:00:00Z",
    },
    {
      chapter: chapter("c3", "Équilibrer une réaction", "physique_chimie"),
      score: 30,
      state: "non_acquis",
      next_review_at: null,
      updated_at: "2026-11-07T10:00:00Z",
    },
  ],
  review_today: [
    {
      reason: "to_finish",
      exercise: exercise("pa1", "Variations"),
      attempt: "at1",
      due_at: "2026-11-07T10:00:00Z",
      last_score: null,
    },
  ],
};

function server(progress: unknown = PROGRESS, pages: Record<string, unknown> = {}) {
  return mockApi((request) => {
    const url = new URL(request.url);
    if (url.pathname === "/api/progress/") return json(200, progress);
    if (url.pathname === "/api/exercises/") {
      const cursor = url.searchParams.get("cursor") ?? "";
      return json(200, pages[cursor] ?? { next: null, previous: null, results: [] });
    }
    return undefined;
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("écran Progrès", () => {
  it("résume l'activité, les matières et la maîtrise par chapitre", async () => {
    server();
    renderApp("/progres", { authenticated: true });

    expect(await screen.findByText("parcours terminés")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("71")).toBeInTheDocument();
    expect(screen.getByText("jours d'affilée")).toBeInTheDocument();

    expect(screen.getByRole("meter", { name: "Score moyen en Mathématiques" })).toHaveAttribute(
      "aria-valuenow",
      "74",
    );
    // État écrit en toutes lettres, pas seulement en couleur.
    expect(screen.getAllByText("Maîtrisé")).toHaveLength(1);
    expect(screen.getAllByRole("meter", { name: "Maîtrise de Dérivation" })[0]).toHaveAttribute(
      "aria-valuenow",
      "58",
    );

    const reviewLink = screen.getByRole("link", { name: /Variations/ });
    expect(reviewLink).toHaveAttribute("href", "/parcours/pa1?tentative=at1");
  });

  it("met en avant les points faibles, du plus faible au moins faible", async () => {
    server();
    renderApp("/progres", { authenticated: true });
    const weak = (await screen.findByRole("heading", { name: "Points faibles" })).parentElement!;
    const names = within(weak)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(names[0]).toMatch(/Équilibrer une réaction/);
    expect(names[1]).toMatch(/Dérivation/);
    expect(names.some((n) => n?.includes("Calcul littéral"))).toBe(false);
  });

  it("filtre les chapitres par matière", async () => {
    server();
    renderApp("/progres", { authenticated: true });
    await userEvent.click(await screen.findByRole("button", { name: "Physique-Chimie" }));
    expect(screen.getByRole("button", { name: "Physique-Chimie" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText("Calcul littéral")).not.toBeInTheDocument();
    expect(screen.getAllByText("Équilibrer une réaction").length).toBeGreaterThan(0);
  });

  it("explique l'absence de chapitres et invite à scanner sans activité", async () => {
    server({
      summary: { exercises_done: 0, attempts_finished: 0, average_score: null, streak_days: 0 },
      subjects: [],
      chapters: [],
      review_today: [],
    });
    renderApp("/progres", { authenticated: true });
    expect(await screen.findByText(/Termine ton premier parcours/)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText(/rattachés à un chapitre du programme/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Scanner un exercice" })).toHaveAttribute("href", "/scanner");
  });

  it("liste mes parcours page par page (curseur)", async () => {
    const calls = server(PROGRESS, {
      "": {
        next: "http://localhost/api/exercises/?cursor=abc",
        previous: null,
        results: [exercise("e1", "Développer et réduire")],
      },
      abc: { next: null, previous: null, results: [exercise("e2", "", "generating")] },
    });
    renderApp("/progres", { authenticated: true });
    expect(await screen.findByRole("link", { name: /Développer et réduire/ })).toHaveAttribute(
      "href",
      "/parcours/e1",
    );
    await userEvent.click(screen.getByRole("button", { name: "Afficher plus" }));
    expect(await screen.findAllByText("En préparation")).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Afficher plus" })).not.toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/exercises/")).toBe(true);
  });
});
