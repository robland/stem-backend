import { cn, Input } from "@stem/ui";
import { useId } from "react";
import { checkBalance, parseFormula } from "../math/chemistry";
import { RichText } from "../RichText";
import { s } from "../strings";
import type { ActivityDefinition, ActivityOf } from "../types";

// --- Équilibrage ---------------------------------------------------------------------------------

type CoefficientsValue = { coefficients: number[] };
const MAX_COEFFICIENT = 20;

const species = (activity: ActivityOf<"chem_balance">) => [...activity.reactants, ...activity.products];

/** Équation `\ce{…}` avec les coefficients choisis (1 n'est pas écrit). */
export function equationLatex(reactants: string[], products: string[], coefficients: number[]) {
  const side = (list: string[], offset: number) =>
    list
      .map((f, i) => `${(coefficients[offset + i] ?? 1) === 1 ? "" : coefficients[offset + i]}${f}`)
      .join(" + ");
  return `\\ce{${side(reactants, 0)} -> ${side(products, reactants.length)}}`;
}

export const chemBalance: ActivityDefinition<ActivityOf<"chem_balance">, CoefficientsValue> = {
  initial: (activity) => ({ coefficients: species(activity).map(() => 1) }),
  isComplete: (activity, value) => value?.coefficients.length === species(activity).length,
  Renderer({ activity, value, onChange, disabled }) {
    const all = species(activity);
    const coefficients = value?.coefficients ?? all.map(() => 1);
    const check = checkBalance(activity.reactants, activity.products, coefficients);
    const set = (i: number, delta: number) =>
      onChange({
        coefficients: coefficients.map((c, j) =>
          j === i ? Math.min(MAX_COEFFICIENT, Math.max(1, c + delta)) : c,
        ),
      });
    const stepper = (formula: string, i: number) => (
      <div
        key={i}
        className="border-border bg-surface flex flex-col items-center gap-1 rounded-lg border p-2"
      >
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label={s.balanceMinus(formula)}
            disabled={disabled || coefficients[i] === 1}
            onClick={() => set(i, -1)}
            className="min-h-touch min-w-touch border-border hover:bg-surface-2 rounded-lg border text-xl font-bold disabled:opacity-30"
          >
            −
          </button>
          <output
            aria-label={s.balanceCoefficient(formula)}
            aria-live="polite"
            className="min-w-8 text-center text-2xl font-bold"
          >
            {coefficients[i]}
          </output>
          <button
            type="button"
            aria-label={s.balancePlus(formula)}
            disabled={disabled || coefficients[i] === MAX_COEFFICIENT}
            onClick={() => set(i, 1)}
            className="min-h-touch min-w-touch border-border hover:bg-surface-2 rounded-lg border text-xl font-bold disabled:opacity-30"
          >
            +
          </button>
        </div>
        <RichText text={`\\ce{${formula}}`} />
      </div>
    );
    return (
      <div className="flex flex-col gap-4">
        <div className="bg-surface-2 overflow-x-auto rounded-lg p-3 text-center text-xl">
          <RichText text={`$${equationLatex(activity.reactants, activity.products, coefficients)}$`} />
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {activity.reactants.map((f, i) => stepper(f, i))}
          <span aria-hidden className="text-2xl">
            →
          </span>
          {activity.products.map((f, i) => stepper(f, activity.reactants.length + i))}
        </div>
        {check ? (
          <table className="w-full text-center text-sm">
            <caption className="mb-1 text-left font-semibold">{s.balanceCount}</caption>
            <thead>
              <tr className="text-muted">
                <th scope="col">{s.balanceElement}</th>
                <th scope="col">{s.balanceLeft}</th>
                <th scope="col">{s.balanceRight}</th>
              </tr>
            </thead>
            <tbody>
              {check.elements.map((e) => (
                <tr
                  key={e.element}
                  className={cn(e.left === e.right ? "text-success" : "text-danger", "font-semibold")}
                >
                  <th scope="row">{e.element}</th>
                  <td>{e.left}</td>
                  <td>{e.right}</td>
                </tr>
              ))}
              {check.charge.left !== 0 || check.charge.right !== 0 ? (
                <tr
                  className={cn(
                    check.charge.left === check.charge.right ? "text-success" : "text-danger",
                    "font-semibold",
                  )}
                >
                  <th scope="row">{s.balanceCharge}</th>
                  <td>{check.charge.left}</td>
                  <td>{check.charge.right}</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        ) : null}
      </div>
    );
  },
};

// --- Formule chimique ----------------------------------------------------------------------------

type FormulaValue = { formula: string };

export const chemFormula: ActivityDefinition<ActivityOf<"chem_formula">, FormulaValue> = {
  isComplete: (_a, value) => Boolean(value?.formula.trim()),
  Renderer({ value, onChange, disabled }) {
    const id = useId();
    const text = value?.formula ?? "";
    const readable = text.trim() ? parseFormula(text) !== null : false;
    return (
      <div className="flex flex-col gap-2">
        <label htmlFor={id} className="text-sm font-semibold">
          {s.chemFormula}
        </label>
        <Input
          id={id}
          value={text}
          onChange={(e) => onChange({ formula: e.target.value })}
          disabled={disabled}
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          aria-describedby={`${id}-hint`}
          className="font-mono text-lg"
        />
        <p id={`${id}-hint`} className="text-muted text-sm">
          {s.chemFormulaHint}
        </p>
        {readable ? (
          <p aria-hidden className="text-2xl">
            <RichText text={`\\ce{${text.trim()}}`} />
          </p>
        ) : null}
      </div>
    );
  },
};

// --- Conversion d'unités -------------------------------------------------------------------------

type ConversionValue = { value: string };

/** Le texte saisi est envoyé tel quel : l'API lit les nombres français (virgule, espaces, 2,5×10^3). */
export const unitConversion: ActivityDefinition<ActivityOf<"unit_conversion">, ConversionValue> = {
  isComplete: (_a, value) => Boolean(value?.value.trim()),
  Renderer({ activity, value, onChange, disabled }) {
    const id = useId();
    return (
      <div className="flex flex-wrap items-center gap-2 text-xl">
        <span>
          {String(activity.value).replace(".", ",")} {activity.from_unit} =
        </span>
        <Input
          id={id}
          aria-label={s.conversion(activity.from_unit, activity.to_unit)}
          value={value?.value ?? ""}
          onChange={(e) => onChange({ value: e.target.value })}
          disabled={disabled}
          inputMode="decimal"
          autoComplete="off"
          className="w-40 text-xl"
        />
        <span>{activity.to_unit}</span>
      </div>
    );
  },
};
