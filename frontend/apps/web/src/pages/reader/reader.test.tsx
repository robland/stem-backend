import { exerciseContent, step, toPublic } from "@stem/content-schema/fixtures";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { json, mockApi, renderApp } from "@/test-utils";

const CONTENT = toPublic(exerciseContent([step("s1", "mcq"), step("s2", "true_false")]));
const EXERCISE = {
  id: "pa1",
  title: CONTENT.title,
  subject: "maths",
  chapter: null,
  level: "1re",
  exam: "BAC",
  generation_status: "ready",
  error_message: "",
  created_at: "2026-11-07T10:00:00Z",
  schema_version: "1.1",
  content: CONTENT,
};

type StepState = {
  step_id: string;
  status: "pending" | "succeeded" | "failed";
  wrong_answers: number;
  hints_used: number;
  score: number;
};

/** Faux serveur de tentatives : correction du QCM (b) et du vrai/faux (vrai), règles de score du backend. */
function fakeServer({ attemptId = "at1", startAt = "s1", failNetworkOnce = false } = {}) {
  const steps: StepState[] = ["s1", "s2"].map((id) => ({
    step_id: id,
    status: "pending",
    wrong_answers: 0,
    hints_used: 0,
    score: 0,
  }));
  if (startAt === "s2") Object.assign(steps[0]!, { status: "succeeded", score: 100 });
  let networkFailed = !failNetworkOnce;
  const attempt = () => {
    const current = steps.find((s) => s.status === "pending")?.step_id ?? null;
    return {
      id: attemptId,
      exercise: "pa1",
      mode: "solo",
      started_at: "2026-11-07T10:00:00Z",
      finished_at: current ? null : "2026-11-07T10:05:00Z",
      score: Math.round(steps.reduce((a, s) => a + s.score, 0) / steps.length),
      hints_used: steps.reduce((a, s) => a + s.hints_used, 0),
      current_step_id: current,
      steps,
    };
  };
  const calls = mockApi((request, body) => {
    const path = new URL(request.url).pathname;
    if (path === "/api/exercises/pa1/") return json(200, EXERCISE);
    if (path === "/api/exercises/pa1/attempts/") return json(201, attempt());
    if (path === `/api/attempts/${attemptId}/`) return json(200, attempt());
    if (path === `/api/attempts/${attemptId}/hints/`) {
      const state = steps.find((s) => s.step_id === (body as { step_id: string }).step_id)!;
      state.hints_used += 1;
      return json(200, {
        step_id: state.step_id,
        hint: `Indice serveur ${state.hints_used}`,
        level: state.hints_used,
        total: 3,
      });
    }
    if (path === `/api/attempts/${attemptId}/answers/`) {
      if (!networkFailed) {
        networkFailed = true;
        throw new TypeError("Failed to fetch");
      }
      const { step_id, response } = body as { step_id: string; response: Record<string, unknown> };
      const state = steps.find((s) => s.step_id === step_id)!;
      const correct =
        step_id === "s1"
          ? JSON.stringify(response) === JSON.stringify({ option_ids: ["b"] })
          : response.value === true;
      if (correct) {
        state.status = "succeeded";
        state.score = Math.max(0, 100 - 20 * state.hints_used - 20 * state.wrong_answers);
      } else {
        state.wrong_answers += 1;
      }
      return json(201, {
        is_correct: correct,
        feedback: correct ? null : "Regarde la plus grande puissance de $x$.",
        details: {},
        step: state,
        explanation: correct ? "$f$ est de degré 2." : null,
        attempt: attempt(),
      });
    }
    return undefined;
  });
  return calls;
}

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("lecteur de parcours", () => {
  it("intro → intuition → rappels → étapes avec erreur ciblée → bilan", async () => {
    const calls = fakeServer();
    renderApp("/parcours/pa1", { authenticated: true });

    expect(await screen.findByRole("heading", { name: CONTENT.title })).toBeInTheDocument();
    expect(screen.getByText("2 étapes")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Commencer" }));

    expect(await screen.findByText("Une colline à l'envers.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    expect(await screen.findByText("Dérivée d'une puissance.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));

    // Étape 1 : QCM, d'abord une erreur.
    await userEvent.click(await screen.findByLabelText("1"));
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    expect(await screen.findByText("Pas tout à fait…")).toBeInTheDocument();
    expect(screen.getByText("2 essais restants pour cette étape.")).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: "Corriger ma réponse" });
    expect(retry).toBeDisabled(); // même réponse : il faut la modifier
    await userEvent.click(screen.getByLabelText("2"));
    await userEvent.click(retry);
    expect(await screen.findByText("C'est juste, bien corrigé !")).toBeInTheDocument();
    expect(screen.getByText("La correction")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Étape suivante" }));

    // Étape 2 : vrai/faux, dernière étape.
    await userEvent.click(await screen.findByRole("radio", { name: "Vrai" }));
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    await userEvent.click(await screen.findByRole("button", { name: "Voir le bilan" }));

    expect(await screen.findByRole("heading", { name: "Parcours terminé !" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Score : 90 sur 100" })).toBeInTheDocument();
    expect(screen.getByText("1 erreur")).toBeInTheDocument();

    const answers = calls
      .filter((c) => c.path === "/api/attempts/at1/answers/")
      .map((c) => c.body as Record<string, unknown>);
    expect(answers.map((a) => a.response)).toEqual([
      { option_ids: ["a"] },
      { option_ids: ["b"] },
      { value: true },
    ]);
    expect(new Set(answers.map((a) => a.client_uuid)).size).toBe(3);
    // L'identifiant de tentative vient du client (idempotence) et est mémorisé pour la reprise.
    const start = calls.find((c) => c.path === "/api/exercises/pa1/attempts/")?.body as { id: string };
    expect(start.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(localStorage.getItem("stem.attempt.pa1")).toBe("at1");
  });

  it("donne les indices un par un, avec leur coût", async () => {
    fakeServer();
    renderApp("/parcours/pa1", { authenticated: true });
    await userEvent.click(await screen.findByRole("button", { name: "Commencer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Continuer" }));

    const hint = await screen.findByRole("button", { name: /Indice 1/ });
    expect(hint).toHaveTextContent("−20 points");
    await userEvent.click(hint);
    expect(await screen.findByText("Indice serveur 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Indice 2/ })).toBeInTheDocument();
  });

  it("reprend une tentative en cours à l'étape où l'élève s'était arrêté", async () => {
    localStorage.setItem("stem.attempt.pa1", "at1");
    fakeServer({ startAt: "s2" });
    renderApp("/parcours/pa1", { authenticated: true });
    await userEvent.click(await screen.findByRole("button", { name: "Reprendre où j'en étais" }));
    expect(await screen.findByRole("radio", { name: "Vrai" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Étape 2 sur 2" })).toBeInTheDocument();
  });

  it("renvoie la même réponse avec le même client_uuid après une coupure réseau", async () => {
    const calls = fakeServer({ failNetworkOnce: true });
    renderApp("/parcours/pa1", { authenticated: true });
    await userEvent.click(await screen.findByRole("button", { name: "Commencer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByRole("button", { name: "Continuer" }));
    await userEvent.click(await screen.findByLabelText("2"));
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    expect(await screen.findByText(/Connexion impossible/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    await waitFor(() => expect(screen.getByText("Bravo, c'est juste !")).toBeInTheDocument());

    const uuids = calls
      .filter((c) => c.path === "/api/attempts/at1/answers/")
      .map((c) => (c.body as { client_uuid: string }).client_uuid);
    expect(uuids).toHaveLength(2);
    expect(uuids[0]).toBe(uuids[1]);
  });
});
