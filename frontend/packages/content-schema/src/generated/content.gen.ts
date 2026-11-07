// Fichier généré par scripts/generate.mjs — ne pas modifier à la main (`pnpm schema:generate`).
// Source : stem_learning_app/schemas/exercise-content.schema.json (schema_version 1.1).
import { z } from "zod";

export const SCHEMA_VERSION = "1.1";

export const Axes = z
  .object({ x_max: z.number(), x_min: z.number(), y_max: z.number(), y_min: z.number() })
  .strict();
export type Axes = z.infer<typeof Axes>;

export const Blank = z.object({ accepted: z.array(z.string()), id: z.string() }).strict();
export type Blank = z.infer<typeof Blank>;

export const ChemBalanceAnswer = z.object({ coefficients: z.array(z.number().int()) }).strict();
export type ChemBalanceAnswer = z.infer<typeof ChemBalanceAnswer>;

export const ChemBalanceActivity = z
  .object({
    answer: ChemBalanceAnswer,
    grading: z.literal("chem_balance"),
    products: z.array(z.string()),
    prompt: z.string(),
    reactants: z.array(z.string()),
    type: z.literal("chem_balance"),
  })
  .strict();
export type ChemBalanceActivity = z.infer<typeof ChemBalanceActivity>;

export const ChemFormulaAnswer = z.object({ formula: z.string() }).strict();
export type ChemFormulaAnswer = z.infer<typeof ChemFormulaAnswer>;

export const ChemFormulaActivity = z
  .object({
    answer: ChemFormulaAnswer,
    grading: z.literal("exact"),
    prompt: z.string(),
    type: z.literal("chem_formula"),
  })
  .strict();
export type ChemFormulaActivity = z.infer<typeof ChemFormulaActivity>;

export const CommonMistake = z.object({ feedback: z.string(), pattern: z.string() }).strict();
export type CommonMistake = z.infer<typeof CommonMistake>;

export const FillBlanksAnswer = z.object({ blanks: z.array(Blank) }).strict();
export type FillBlanksAnswer = z.infer<typeof FillBlanksAnswer>;

export const FillBlanksActivity = z
  .object({
    answer: FillBlanksAnswer,
    grading: z.literal("normalized_text"),
    prompt: z.string(),
    text: z.string(),
    type: z.literal("fill_blanks"),
  })
  .strict();
export type FillBlanksActivity = z.infer<typeof FillBlanksActivity>;

export const FormulaAnswer = z
  .object({
    expression: z.string(),
    form: z.enum(["any", "expanded", "factored", "irreducible_fraction"]),
    source: z.string().nullable(),
    variables: z.array(z.string()),
  })
  .strict();
export type FormulaAnswer = z.infer<typeof FormulaAnswer>;

export const FormulaInputActivity = z
  .object({
    answer: FormulaAnswer,
    grading: z.literal("symbolic"),
    prompt: z.string(),
    type: z.literal("formula_input"),
  })
  .strict();
export type FormulaInputActivity = z.infer<typeof FormulaInputActivity>;

export const ParameterValue = z.object({ name: z.string(), value: z.number() }).strict();
export type ParameterValue = z.infer<typeof ParameterValue>;

export const GraphParametersAnswer = z.object({ values: z.array(ParameterValue) }).strict();
export type GraphParametersAnswer = z.infer<typeof GraphParametersAnswer>;

export const Slider = z
  .object({ initial: z.number(), max: z.number(), min: z.number(), name: z.string(), step: z.number() })
  .strict();
export type Slider = z.infer<typeof Slider>;

export const GraphParametersActivity = z
  .object({
    answer: GraphParametersAnswer,
    axes: Axes,
    function: z.string(),
    grading: z.literal("numeric"),
    prompt: z.string(),
    sliders: z.array(Slider),
    tolerance: z.number(),
    type: z.literal("graph_parameters"),
  })
  .strict();
export type GraphParametersActivity = z.infer<typeof GraphParametersActivity>;

export const Point = z.object({ x: z.number(), y: z.number() }).strict();
export type Point = z.infer<typeof Point>;

export const GraphPointsAnswer = z.object({ function: z.string(), points: z.array(Point) }).strict();
export type GraphPointsAnswer = z.infer<typeof GraphPointsAnswer>;

export const GraphPointsActivity = z
  .object({
    answer: GraphPointsAnswer,
    axes: Axes,
    grading: z.literal("numeric"),
    points_to_place: z.array(z.number()),
    prompt: z.string(),
    tolerance: z.number(),
    type: z.literal("graph_points"),
  })
  .strict();
export type GraphPointsActivity = z.infer<typeof GraphPointsActivity>;

export const Intuition = z.object({ example: z.string(), mental_image: z.string() }).strict();
export type Intuition = z.infer<typeof Intuition>;

export const Item = z.object({ content: z.string(), id: z.string() }).strict();
export type Item = z.infer<typeof Item>;

export const Pair = z.object({ left_id: z.string(), right_id: z.string() }).strict();
export type Pair = z.infer<typeof Pair>;

export const MatchingAnswer = z.object({ pairs: z.array(Pair) }).strict();
export type MatchingAnswer = z.infer<typeof MatchingAnswer>;

export const MatchingActivity = z
  .object({
    answer: MatchingAnswer,
    grading: z.literal("exact"),
    left: z.array(Item),
    prompt: z.string(),
    right: z.array(Item),
    type: z.literal("matching"),
  })
  .strict();
export type MatchingActivity = z.infer<typeof MatchingActivity>;

export const McqAnswer = z.object({ option_ids: z.array(z.string()) }).strict();
export type McqAnswer = z.infer<typeof McqAnswer>;

export const McqActivity = z
  .object({
    answer: McqAnswer,
    grading: z.literal("exact"),
    multiple: z.boolean(),
    options: z.array(Item),
    prompt: z.string(),
    type: z.literal("mcq"),
  })
  .strict();
export type McqActivity = z.infer<typeof McqActivity>;

export const OrderingAnswer = z.object({ order: z.array(z.string()) }).strict();
export type OrderingAnswer = z.infer<typeof OrderingAnswer>;

export const OrderingActivity = z
  .object({
    answer: OrderingAnswer,
    grading: z.literal("exact"),
    items: z.array(Item),
    prompt: z.string(),
    type: z.literal("ordering"),
  })
  .strict();
export type OrderingActivity = z.infer<typeof OrderingActivity>;

export const Recall = z
  .object({
    content: z.string(),
    explanation: z.string(),
    kind: z.enum(["formula", "definition", "property", "method"]),
  })
  .strict();
export type Recall = z.infer<typeof Recall>;

export const ShortAnswerAnswer = z
  .object({
    accepted: z.array(z.string()),
    tolerance: z.number().nullable(),
    unit: z.string().nullable(),
    value: z.number().nullable(),
  })
  .strict();
export type ShortAnswerAnswer = z.infer<typeof ShortAnswerAnswer>;

export const ShortAnswerActivity = z
  .object({
    answer: ShortAnswerAnswer,
    grading: z.enum(["normalized_text", "numeric"]),
    prompt: z.string(),
    type: z.literal("short_answer"),
  })
  .strict();
export type ShortAnswerActivity = z.infer<typeof ShortAnswerActivity>;

export const TrueFalseAnswer = z.object({ value: z.boolean() }).strict();
export type TrueFalseAnswer = z.infer<typeof TrueFalseAnswer>;

export const TrueFalseActivity = z
  .object({
    answer: TrueFalseAnswer,
    grading: z.literal("exact"),
    prompt: z.string(),
    type: z.literal("true_false"),
  })
  .strict();
export type TrueFalseActivity = z.infer<typeof TrueFalseActivity>;

export const VariationTableAnswer = z
  .object({
    arrows: z.array(z.enum(["up", "down"])),
    function: z.string().nullable(),
    signs: z.array(z.enum(["+", "-"])),
  })
  .strict();
export type VariationTableAnswer = z.infer<typeof VariationTableAnswer>;

export const VariationTableActivity = z
  .object({
    answer: VariationTableAnswer,
    grading: z.literal("exact"),
    prompt: z.string(),
    type: z.literal("variation_table"),
    x_values: z.array(z.string()),
  })
  .strict();
export type VariationTableActivity = z.infer<typeof VariationTableActivity>;

export const UnitConversionAnswer = z.object({ value: z.number() }).strict();
export type UnitConversionAnswer = z.infer<typeof UnitConversionAnswer>;

export const UnitConversionActivity = z
  .object({
    answer: UnitConversionAnswer,
    from_unit: z.string(),
    grading: z.literal("numeric"),
    prompt: z.string(),
    to_unit: z.string(),
    tolerance: z.number(),
    type: z.literal("unit_conversion"),
    value: z.number(),
  })
  .strict();
export type UnitConversionActivity = z.infer<typeof UnitConversionActivity>;

export const Step = z
  .object({
    activity: z.discriminatedUnion("type", [
      McqActivity,
      TrueFalseActivity,
      ShortAnswerActivity,
      FillBlanksActivity,
      MatchingActivity,
      OrderingActivity,
      FormulaInputActivity,
      GraphPointsActivity,
      GraphParametersActivity,
      VariationTableActivity,
      ChemBalanceActivity,
      ChemFormulaActivity,
      UnitConversionActivity,
    ]),
    common_mistakes: z.array(CommonMistake),
    explanation: z.string(),
    hints: z.array(z.string()),
    id: z.string().regex(new RegExp("^s[0-9]{1,2}$")),
    objective: z.string(),
    skill: z.string().regex(new RegExp("^[a-z0-9_]{1,60}$")),
  })
  .strict();
export type Step = z.infer<typeof Step>;

export const Summary = z.object({ key_takeaway: z.string() }).strict();
export type Summary = z.infer<typeof Summary>;

export const ExerciseContent = z
  .object({
    intuition: Intuition,
    recall: z.array(Recall),
    schema_version: z.literal("1.1"),
    statement: z.string(),
    steps: z.array(Step),
    summary: Summary,
    title: z.string(),
  })
  .strict();
export type ExerciseContent = z.infer<typeof ExerciseContent>;

export const Activity = Step.shape.activity;
export type Activity = z.infer<typeof Activity>;

// Contenu public (`GET /api/exercises/{id}`) : sans réponse attendue, erreurs typiques ni correction,
// et sans le dernier niveau d'indice (obtenu par `POST attempts/{id}/hints`).
export const McqActivityPublic = McqActivity.omit({ answer: true });
export type McqActivityPublic = z.infer<typeof McqActivityPublic>;
export const TrueFalseActivityPublic = TrueFalseActivity.omit({ answer: true });
export type TrueFalseActivityPublic = z.infer<typeof TrueFalseActivityPublic>;
export const ShortAnswerActivityPublic = ShortAnswerActivity.omit({ answer: true });
export type ShortAnswerActivityPublic = z.infer<typeof ShortAnswerActivityPublic>;
export const FillBlanksActivityPublic = FillBlanksActivity.omit({ answer: true });
export type FillBlanksActivityPublic = z.infer<typeof FillBlanksActivityPublic>;
export const MatchingActivityPublic = MatchingActivity.omit({ answer: true });
export type MatchingActivityPublic = z.infer<typeof MatchingActivityPublic>;
export const OrderingActivityPublic = OrderingActivity.omit({ answer: true });
export type OrderingActivityPublic = z.infer<typeof OrderingActivityPublic>;
export const FormulaInputActivityPublic = FormulaInputActivity.omit({ answer: true });
export type FormulaInputActivityPublic = z.infer<typeof FormulaInputActivityPublic>;
export const GraphPointsActivityPublic = GraphPointsActivity.omit({ answer: true });
export type GraphPointsActivityPublic = z.infer<typeof GraphPointsActivityPublic>;
export const GraphParametersActivityPublic = GraphParametersActivity.omit({ answer: true });
export type GraphParametersActivityPublic = z.infer<typeof GraphParametersActivityPublic>;
export const VariationTableActivityPublic = VariationTableActivity.omit({ answer: true });
export type VariationTableActivityPublic = z.infer<typeof VariationTableActivityPublic>;
export const ChemBalanceActivityPublic = ChemBalanceActivity.omit({ answer: true });
export type ChemBalanceActivityPublic = z.infer<typeof ChemBalanceActivityPublic>;
export const ChemFormulaActivityPublic = ChemFormulaActivity.omit({ answer: true });
export type ChemFormulaActivityPublic = z.infer<typeof ChemFormulaActivityPublic>;
export const UnitConversionActivityPublic = UnitConversionActivity.omit({ answer: true });
export type UnitConversionActivityPublic = z.infer<typeof UnitConversionActivityPublic>;

export const ActivityPublic = z.discriminatedUnion("type", [
  McqActivityPublic,
  TrueFalseActivityPublic,
  ShortAnswerActivityPublic,
  FillBlanksActivityPublic,
  MatchingActivityPublic,
  OrderingActivityPublic,
  FormulaInputActivityPublic,
  GraphPointsActivityPublic,
  GraphParametersActivityPublic,
  VariationTableActivityPublic,
  ChemBalanceActivityPublic,
  ChemFormulaActivityPublic,
  UnitConversionActivityPublic,
]);
export type ActivityPublic = z.infer<typeof ActivityPublic>;

export const StepPublic = Step.omit({ common_mistakes: true, explanation: true, activity: true }).extend({
  activity: ActivityPublic,
});
export type StepPublic = z.infer<typeof StepPublic>;

export const ExerciseContentPublic = ExerciseContent.extend({ steps: z.array(StepPublic) });
export type ExerciseContentPublic = z.infer<typeof ExerciseContentPublic>;

export const ACTIVITY_TYPES = [
  "mcq",
  "true_false",
  "short_answer",
  "fill_blanks",
  "matching",
  "ordering",
  "formula_input",
  "graph_points",
  "graph_parameters",
  "variation_table",
  "chem_balance",
  "chem_formula",
  "unit_conversion",
] as const;
export type ActivityType = (typeof ACTIVITY_TYPES)[number];
