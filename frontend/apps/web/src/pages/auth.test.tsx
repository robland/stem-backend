import { getPreferences } from "@/lib/preferences";
import { json, mockApi, renderApp } from "@/test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const ME = {
  phone: "061234567",
  pseudo: "kiki",
  level: "Tle",
  serie: "C",
  date_joined: "2026-11-07T10:00:00Z",
};
const PROGRESS = {
  summary: { exercises_done: 0, attempts_finished: 0, average_score: null, streak_days: 0 },
  subjects: [],
  chapters: [],
  review_today: [],
};

const authedRoutes = (request: Request) => {
  const path = new URL(request.url).pathname;
  if (path === "/api/me/") return json(200, ME);
  if (path === "/api/progress/") return json(200, PROGRESS);
  return undefined;
};

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("connexion", () => {
  it("redirige vers la connexion sans session", async () => {
    mockApi(() => undefined);
    const router = renderApp("/progres");
    expect(await screen.findByRole("heading", { name: "Content de te revoir" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/connexion");
  });

  it("normalise le numéro, se connecte et revient à la page demandée", async () => {
    const calls = mockApi((request, body) => {
      if (new URL(request.url).pathname === "/api/auth/login/") {
        return (body as { phone: string }).phone === "061234567" ? json(200, { access: "A" }) : json(401, {});
      }
      return authedRoutes(request);
    });
    const router = renderApp("/progres");

    await userEvent.type(await screen.findByLabelText("Numéro de téléphone"), "06 12 34 567");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "secret123");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/progres"));
    expect(calls.find((c) => c.path === "/api/auth/login/")?.body).toEqual({
      phone: "061234567",
      password: "secret123",
    });
  });

  it("affiche un message clair si les identifiants sont refusés", async () => {
    mockApi(() => json(401, { detail: "No active account found with the given credentials" }));
    renderApp("/connexion");

    await userEvent.type(await screen.findByLabelText("Numéro de téléphone"), "061234567");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "mauvais");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByText("Numéro ou mot de passe incorrect.")).toBeInTheDocument();
  });

  it("valide le numéro avant l'envoi", async () => {
    const calls = mockApi(() => undefined);
    renderApp("/connexion");
    await userEvent.type(await screen.findByLabelText("Numéro de téléphone"), "12");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByText("Entre un numéro de 8 à 15 chiffres.")).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });
});

describe("inscription", () => {
  async function fillAccount() {
    await userEvent.type(await screen.findByLabelText("Numéro de téléphone"), "06 123 45 67");
    await userEvent.type(screen.getByLabelText("Pseudo"), "Neo");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "motdepasse");
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
  }

  it("crée le compte en 4 étapes, garde matières et objectif sur l'appareil", async () => {
    const calls = mockApi((request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/auth/register/") return json(201, {});
      if (path === "/api/auth/login/") return json(200, { access: "A" });
      return authedRoutes(request);
    });
    const router = renderApp("/inscription");

    await fillAccount();
    await userEvent.click(await screen.findByLabelText("Terminale"));
    await userEvent.click(screen.getByLabelText("Série C"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByLabelText("Physique-Chimie"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    // Objectif présélectionné d'après la classe.
    expect(await screen.findByLabelText(/Le BAC/)).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "C'est parti !" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(await screen.findByRole("heading", { name: "Salut kiki !" })).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/auth/register/")?.body).toEqual({
      phone: "061234567",
      pseudo: "Neo",
      password: "motdepasse",
      level: "Tle",
      serie: "C",
    });
    expect(getPreferences()).toMatchObject({ subjects: ["maths"], goal: "bac" });
  });

  it("exige une série au lycée", async () => {
    mockApi(() => undefined);
    renderApp("/inscription");
    await fillAccount();
    await userEvent.click(await screen.findByLabelText("2nde"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    expect(await screen.findByText("Choisis ta série.")).toBeInTheDocument();
  });

  it("ramène à l'étape du champ refusé par le serveur", async () => {
    mockApi((request) =>
      new URL(request.url).pathname === "/api/auth/register/"
        ? json(400, { phone: ["Ce numéro est déjà utilisé."] })
        : undefined,
    );
    renderApp("/inscription");
    await fillAccount();
    await userEvent.click(await screen.findByLabelText("3e"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByRole("button", { name: "C'est parti !" }));

    expect(await screen.findByText("Ce numéro est déjà utilisé.")).toBeInTheDocument();
    expect(screen.getByLabelText("Numéro de téléphone")).toHaveValue("06 123 45 67");
  });
});
