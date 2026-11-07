import { parseActivity, type ActivityPublic, type ActivityType } from "@stem/content-schema";
import { Alert } from "@stem/ui";
import { RichText } from "./RichText";
import { chemBalance, chemFormula, unitConversion } from "./renderers/chemistry";
import { fillBlanks, matching, mcq, ordering, shortAnswer, trueFalse } from "./renderers/common";
import { formulaInput } from "./renderers/formula";
import { graphParameters, graphPoints } from "./renderers/graph";
import { variationTable } from "./renderers/variation";
import { s } from "./strings";
import type { ActivityDefinition, ActivityOf, GradingDetails } from "./types";

/** Un renderer par `type` d'activité V1 (README frontend §4). */
export const definitions: { [K in ActivityType]: ActivityDefinition<ActivityOf<K>, never> } = {
  mcq,
  true_false: trueFalse,
  short_answer: shortAnswer,
  fill_blanks: fillBlanks,
  matching,
  ordering,
  formula_input: formulaInput,
  graph_points: graphPoints,
  graph_parameters: graphParameters,
  variation_table: variationTable,
  chem_balance: chemBalance,
  chem_formula: chemFormula,
  unit_conversion: unitConversion,
} as never;

// Vue non typée des définitions, pour le lecteur qui manipule n'importe quel type d'activité.
type AnyDefinition = ActivityDefinition<ActivityPublic, unknown>;
const definitionOf = (activity: ActivityPublic) => definitions[activity.type] as unknown as AnyDefinition;

export const initialAnswer = (activity: ActivityPublic, seed: string) =>
  definitionOf(activity).initial?.(activity, seed);
export const isAnswerComplete = (activity: ActivityPublic, value: unknown) =>
  definitionOf(activity).isComplete(activity, value);
export const serializeAnswer = (activity: ActivityPublic, value: unknown) => {
  const serialize = definitionOf(activity).serialize;
  return serialize ? serialize(value) : value;
};

type ViewProps = {
  /** Activité brute du contenu : lue isolément pour qu'une étape invalide ne bloque pas le parcours. */
  activity: unknown;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
  details?: GradingDetails;
  seed: string;
};

export function ActivityView({ activity: raw, value, onChange, disabled, details, seed }: ViewProps) {
  const parsed = parseActivity(raw);
  if (!parsed.ok)
    return <Alert tone="info">{parsed.reason === "unknown_type" ? s.unknownType : s.invalidStep}</Alert>;
  const activity = parsed.data;
  const { Renderer, ownsPrompt } = definitionOf(activity);
  return (
    <div className="flex flex-col gap-4">
      {ownsPrompt ? null : (
        <p className="text-lg font-semibold leading-relaxed">
          <RichText text={activity.prompt} />
        </p>
      )}
      <Renderer
        activity={activity}
        value={value}
        onChange={onChange}
        disabled={disabled}
        details={details}
        seed={seed}
      />
    </div>
  );
}
