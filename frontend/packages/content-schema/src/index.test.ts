import { ACTIVITIES, exerciseContent, step, toPublic } from "./fixtures";
import { ACTIVITY_TYPES, parseActivity, parseContent, parsePublicContent, type ActivityType } from "./index";

const allSteps = () => ACTIVITY_TYPES.map((type, i) => step(`s${i + 1}`, type));

describe("contenu complet (paquet hors-ligne)", () => {
  it("accepte un parcours avec chacun des 13 types V1", () => {
    expect(ACTIVITY_TYPES).toHaveLength(13);
    const result = parseContent(exerciseContent(allSteps()));
    expect(result.ok).toBe(true);
  });

  it("refuse un champ inconnu (contrat strict)", () => {
    const content = { ...exerciseContent(), extra: 1 };
    expect(parseContent(content).ok).toBe(false);
  });

  it("refuse une autre version de schéma", () => {
    expect(parseContent(exerciseContent([], { schema_version: "1.0" as "1.1" })).ok).toBe(false);
  });

  it("refuse un identifiant d'étape mal formé", () => {
    expect(parseContent(exerciseContent([step("etape1")])).ok).toBe(false);
  });
});

describe("contenu public (GET /api/exercises/{id})", () => {
  it("accepte le contenu sans réponses", () => {
    const result = parsePublicContent(toPublic(exerciseContent(allSteps())));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.steps[0]).not.toHaveProperty("explanation");
      expect(result.data.steps[0]?.hints).toHaveLength(2);
    }
  });

  it("refuse un contenu public qui contiendrait encore la réponse", () => {
    expect(parsePublicContent(exerciseContent()).ok).toBe(false);
  });
});

describe("parseActivity", () => {
  it.each(ACTIVITY_TYPES)("lit l'activité publique %s", (type: ActivityType) => {
    const { answer: _answer, ...activity } = ACTIVITIES[type];
    expect(parseActivity(activity)).toEqual({ ok: true, data: activity });
  });

  it("signale un type inconnu (schéma plus récent)", () => {
    expect(parseActivity({ type: "timeline", prompt: "…" })).toEqual({ ok: false, reason: "unknown_type" });
  });

  it("signale une activité mal formée", () => {
    expect(parseActivity({ type: "mcq", prompt: "?" })).toEqual({ ok: false, reason: "invalid" });
  });
});
