import type { ActivityType } from "@stem/content-schema";
import { ACTIVITIES } from "@stem/content-schema/fixtures";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { fillPlaceholder, previewExpression } from "./renderers/formula";
import { niceStep, parseNumber } from "./renderers/graph";
import { ActivityView, initialAnswer, isAnswerComplete, serializeAnswer } from "./registry";
import { shuffle } from "./random";
import type { GradingDetails } from "./types";

const publicActivity = <T extends ActivityType>(type: T) => {
  const { answer: _answer, ...activity } = ACTIVITIES[type];
  return activity;
};

/** Monte une activité et expose la réponse sérialisée et l'état « complet ». */
function setup(type: ActivityType, details?: GradingDetails, overrides: Record<string, unknown> = {}) {
  const activity = { ...publicActivity(type), ...overrides } as never;
  const state = { value: undefined as unknown };
  function Harness() {
    const [value, setValue] = useState<unknown>(() => initialAnswer(activity, "s1"));
    state.value = value;
    return <ActivityView activity={activity} value={value} onChange={setValue} details={details} seed="s1" />;
  }
  render(<Harness />);
  return {
    response: () => serializeAnswer(activity, state.value),
    complete: () => isAnswerComplete(activity, state.value),
  };
}

describe("mcq", () => {
  it("une seule option quand multiple = false", async () => {
    const { response, complete } = setup("mcq");
    expect(complete()).toBe(false);
    await userEvent.click(screen.getByLabelText("1"));
    await userEvent.click(screen.getByLabelText("2"));
    expect(response()).toEqual({ option_ids: ["b"] });
    expect(complete()).toBe(true);
  });

  it("plusieurs options quand multiple = true", async () => {
    const { response } = setup("mcq", null, { multiple: true });
    await userEvent.click(screen.getByLabelText("1"));
    await userEvent.click(screen.getByLabelText("2"));
    expect(response()).toEqual({ option_ids: ["a", "b"] });
  });
});

describe("true_false", () => {
  it("envoie un booléen", async () => {
    const { response } = setup("true_false");
    await userEvent.click(screen.getByRole("radio", { name: "Faux" }));
    expect(response()).toEqual({ value: false });
  });
});

describe("short_answer", () => {
  it("envoie le texte saisi, clavier décimal en mode numérique", async () => {
    const { response } = setup("short_answer");
    const input = screen.getByLabelText("Ta réponse");
    expect(input).toHaveAttribute("inputmode", "decimal");
    await userEvent.type(input, "3,0");
    expect(response()).toEqual({ text: "3,0" });
  });
});

describe("fill_blanks", () => {
  it("un champ par trou, dans l'ordre du texte", async () => {
    const { response, complete } = setup("fill_blanks");
    await userEvent.type(screen.getByLabelText("Trou 1"), "2");
    expect(complete()).toBe(false);
    await userEvent.type(screen.getByLabelText("Trou 2"), "-1");
    expect(response()).toEqual({
      blanks: [
        { id: "1", text: "2" },
        { id: "2", text: "-1" },
      ],
    });
    expect(complete()).toBe(true);
  });

  it("marque le trou faux d'après details", () => {
    setup("fill_blanks", { blanks: { "1": true, "2": false } });
    expect(screen.getByLabelText("Trou 2")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Trou 1")).not.toHaveAttribute("aria-invalid");
  });
});

describe("matching", () => {
  it("associe par touchers successifs", async () => {
    const { response, complete } = setup("matching");
    const right = within(screen.getByRole("list", { name: "Correspondances possibles" })).getAllByRole(
      "button",
    );
    // Le premier élément de gauche est actif d'emblée ; on lui associe le premier choix affiché, etc.
    await userEvent.click(right[0]!);
    await userEvent.click(right[1]!);
    expect(complete()).toBe(true);
    const pairs = (response() as { pairs: { left_id: string; right_id: string }[] }).pairs;
    expect(pairs.map((p) => p.left_id).sort()).toEqual(["l1", "l2"]);
    expect(new Set(pairs.map((p) => p.right_id)).size).toBe(2);
  });
});

describe("ordering", () => {
  it("part d'un ordre mélangé et réordonne avec les flèches", async () => {
    const { response } = setup("ordering");
    expect(response()).toEqual({ order: ["i2", "i1"] }); // jamais l'ordre d'origine
    await userEvent.click(screen.getByRole("button", { name: "Descendre l'élément 1" }));
    expect(response()).toEqual({ order: ["i1", "i2"] });
  });
});

describe("formula_input", () => {
  it("affiche l'expression dans la case de la consigne et envoie de l'ASCII", async () => {
    const { response, complete } = setup("formula_input");
    const input = screen.getByLabelText("Ton expression");
    await userEvent.type(input, "2x");
    await userEvent.click(screen.getByRole("button", { name: "au carré" }));
    expect(input).toHaveValue("2x^2");
    await userEvent.type(input, "−4");
    expect(complete()).toBe(true);
    expect(response()).toEqual({ expression: "2x^2-4" });
  });

  it("signale une expression illisible et bloque l'envoi", async () => {
    const { complete } = setup("formula_input");
    await userEvent.type(screen.getByLabelText("Ton expression"), "(x+1");
    expect(screen.getByText("Une parenthèse n'est pas fermée.")).toBeInTheDocument();
    expect(complete()).toBe(false);
  });

  it("fillPlaceholder et previewExpression", () => {
    expect(fillPlaceholder("$f'(x) = \\placeholder{}$", "2x")).toBe("$f'(x) = \\boxed{2x}$");
    expect(fillPlaceholder("$f'(x) = \\placeholder{}$", null)).toBe("$f'(x) = \\boxed{\\phantom{x}}$");
    expect(previewExpression("x +")).toEqual({ latex: null, error: "Il manque un nombre ou une lettre." });
  });
});

describe("graph_points", () => {
  it("place les points par la saisie des ordonnées", async () => {
    const { response, complete } = setup("graph_points");
    const y0 = screen.getByLabelText("Ordonnée du point d'abscisse 0");
    await userEvent.type(y0, "3");
    fireEvent.blur(y0);
    expect(complete()).toBe(false);
    const y2 = screen.getByLabelText("Ordonnée du point d'abscisse 2");
    await userEvent.type(y2, "-1,5");
    fireEvent.blur(y2);
    expect(response()).toEqual({
      points: [
        { x: 0, y: 3 },
        { x: 2, y: -1.5 },
      ],
    });
    expect(complete()).toBe(true);
  });
});

describe("graph_parameters", () => {
  it("part des valeurs initiales et suit les curseurs", () => {
    const { response } = setup("graph_parameters");
    expect(response()).toEqual({
      values: [
        { name: "a", value: 0 },
        { name: "b", value: 0 },
      ],
    });
    fireEvent.change(screen.getByLabelText("Valeur de a"), { target: { value: "2" } });
    expect(response()).toEqual({
      values: [
        { name: "a", value: 2 },
        { name: "b", value: 0 },
      ],
    });
  });
});

describe("variation_table", () => {
  it("un signe et une flèche par intervalle", async () => {
    const { response, complete } = setup("variation_table");
    await userEvent.click(screen.getByRole("button", { name: "Signe sur l'intervalle 1 : à choisir" }));
    await userEvent.click(screen.getByRole("button", { name: "Signe sur l'intervalle 1 : positif" }));
    await userEvent.click(screen.getByRole("button", { name: "Signe sur l'intervalle 2 : à choisir" }));
    await userEvent.click(screen.getByRole("button", { name: "Variation sur l'intervalle 1 : à choisir" }));
    await userEvent.click(screen.getByRole("button", { name: "Variation sur l'intervalle 1 : croissante" }));
    expect(complete()).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Variation sur l'intervalle 2 : à choisir" }));
    expect(response()).toEqual({ signs: ["-", "+"], arrows: ["down", "up"] });
    expect(complete()).toBe(true);
  });
});

describe("chem_balance", () => {
  it("ajuste les coefficients et compte les atomes", async () => {
    const { response } = setup("chem_balance");
    expect(response()).toEqual({ coefficients: [1, 1, 1] });
    const oxygen = screen.getByRole("row", { name: /^O/ });
    expect(
      within(oxygen)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["2", "1"]);
    await userEvent.click(screen.getByRole("button", { name: "Augmenter le coefficient de H2" }));
    await userEvent.click(screen.getByRole("button", { name: "Augmenter le coefficient de H2O" }));
    expect(response()).toEqual({ coefficients: [2, 1, 2] });
    expect(
      within(screen.getByRole("row", { name: /^O/ }))
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["2", "2"]);
  });
});

describe("chem_formula et unit_conversion", () => {
  it("envoient le texte saisi", async () => {
    const formula = setup("chem_formula");
    await userEvent.type(screen.getByLabelText("Ta formule"), "H2O");
    expect(formula.response()).toEqual({ formula: "H2O" });
  });

  it("conversion : nombre saisi en texte (lu par l'API)", async () => {
    const conversion = setup("unit_conversion");
    await userEvent.type(screen.getByLabelText("Conversion de km en m"), "2 500");
    expect(conversion.response()).toEqual({ value: "2 500" });
  });
});

describe("robustesse", () => {
  it("type inconnu : invite à mettre l'application à jour", () => {
    render(
      <ActivityView
        activity={{ type: "timeline", prompt: "?" }}
        value={undefined}
        onChange={() => {}}
        seed="s1"
      />,
    );
    expect(screen.getByText(/mets l'application à jour/)).toBeInTheDocument();
  });

  it("activité mal formée : état d'erreur, pas de plantage", () => {
    render(
      <ActivityView
        activity={{ type: "mcq", prompt: "?" }}
        value={undefined}
        onChange={() => {}}
        seed="s1"
      />,
    );
    expect(screen.getByText("Cette étape n'a pas pu être affichée.")).toBeInTheDocument();
  });
});

describe("utilitaires", () => {
  it("shuffle est stable et change l'ordre", () => {
    expect(shuffle([1, 2, 3, 4], "s1")).toEqual(shuffle([1, 2, 3, 4], "s1"));
    expect(shuffle([1, 2], "x")).not.toEqual([1, 2]);
  });

  it("niceStep et parseNumber", () => {
    expect(niceStep(10)).toBe(2);
    expect(niceStep(6)).toBe(1);
    expect(parseNumber("−2,5")).toBe(-2.5);
    expect(parseNumber("")).toBeNaN();
  });
});
