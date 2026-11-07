import { cn } from "@stem/ui";
import type { ReactNode } from "react";
import { RichText } from "../RichText";
import { s } from "../strings";
import type { ActivityDefinition, ActivityOf } from "../types";

type Sign = "+" | "-";
type Arrow = "up" | "down";
type TableValue = { signs: (Sign | null)[]; arrows: (Arrow | null)[] };

const nextSign = (v: Sign | null): Sign => (v === "+" ? "-" : "+");
const nextArrow = (v: Arrow | null): Arrow => (v === "up" ? "down" : "up");

const intervals = (activity: ActivityOf<"variation_table">) => Math.max(1, activity.x_values.length - 1);

/**
 * Tableau de variations : 2n + 1 colonnes (valeurs de x aux colonnes paires, intervalles aux impaires),
 * un signe de f′ et une flèche par intervalle, à basculer d'un toucher.
 */
export const variationTable: ActivityDefinition<ActivityOf<"variation_table">, TableValue> = {
  initial: (activity) => ({
    signs: Array(intervals(activity)).fill(null),
    arrows: Array(intervals(activity)).fill(null),
  }),
  isComplete: (activity, value) =>
    Boolean(
      value &&
      value.signs.length === intervals(activity) &&
      value.signs.every(Boolean) &&
      value.arrows.every(Boolean),
    ),
  serialize: (value) => ({ signs: value.signs, arrows: value.arrows }),
  Renderer({ activity, value, onChange, disabled, details }) {
    const n = intervals(activity);
    const signs = value?.signs ?? Array<Sign | null>(n).fill(null);
    const arrows = value?.arrows ?? Array<Arrow | null>(n).fill(null);
    // L'API juge les signes et les flèches en bloc (`details.signs`, `details.arrows`).
    const signsOk = typeof details?.signs === "boolean" ? details.signs : undefined;
    const arrowsOk = typeof details?.arrows === "boolean" ? details.arrows : undefined;
    const rowClass = (ok: boolean | undefined) =>
      ok === true ? "bg-success-soft" : ok === false ? "bg-danger-soft" : "";
    const button =
      "min-h-touch min-w-touch rounded-lg border-2 border-border bg-surface px-2 text-xl font-bold hover:bg-surface-2";
    const columns = Array.from({ length: 2 * n + 1 }, (_, k) => k);
    const row = (render: (interval: number) => ReactNode) =>
      columns.map((k) => (
        <td key={k} className="px-1 py-2">
          {k % 2 === 1 ? render((k - 1) / 2) : null}
        </td>
      ));

    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[18rem] border-collapse text-center">
          <tbody>
            <tr className="border-fg border-b-2">
              <th scope="row" className="border-fg border-r-2 px-2 py-2 text-left font-serif italic">
                {s.variationX}
              </th>
              {columns.map((k) => (
                <td key={k} className="px-1 py-2">
                  {k % 2 === 0 && activity.x_values[k / 2] !== undefined ? (
                    <RichText text={activity.x_values[k / 2]!} />
                  ) : null}
                </td>
              ))}
            </tr>
            <tr className={cn("border-border border-b", rowClass(signsOk))}>
              <th scope="row" className="border-fg border-r-2 px-2 py-2 text-left text-sm">
                {s.variationSign}
              </th>
              {row((i) => (
                <button
                  type="button"
                  disabled={disabled}
                  aria-label={s.variationSignLabel(
                    i + 1,
                    signs[i] === "+" ? s.plus : signs[i] === "-" ? s.minus : s.unset,
                  )}
                  onClick={() =>
                    onChange({ signs: signs.map((v, j) => (j === i ? nextSign(v) : v)), arrows })
                  }
                  className={button}
                >
                  {signs[i] === "-" ? "−" : (signs[i] ?? "?")}
                </button>
              ))}
            </tr>
            <tr className={rowClass(arrowsOk)}>
              <th scope="row" className="border-fg border-r-2 px-2 py-2 text-left text-sm">
                {s.variationArrow}
              </th>
              {row((i) => (
                <button
                  type="button"
                  disabled={disabled}
                  aria-label={s.variationArrowLabel(
                    i + 1,
                    arrows[i] === "up" ? s.up : arrows[i] === "down" ? s.down : s.unset,
                  )}
                  onClick={() =>
                    onChange({ signs, arrows: arrows.map((v, j) => (j === i ? nextArrow(v) : v)) })
                  }
                  className={button}
                >
                  {arrows[i] === "up" ? "↗" : arrows[i] === "down" ? "↘" : "?"}
                </button>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    );
  },
};
