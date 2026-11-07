import { cn, Input, Spinner } from "@stem/ui";
import { lazy, Suspense, useId, useMemo, useRef } from "react";
import { ExpressionError, normalizeExpression, parseExpression, toLatex } from "../math/expression";
import { RichText } from "../RichText";
import { s } from "../strings";
import { useActivitySettings, type ActivityDefinition, type ActivityOf } from "../types";

type FormulaResponse = { expression: string };

const MathLiveField = lazy(() => import("./MathLiveField"));

const PLACEHOLDER_RE = /\\placeholder(\{\})?/;

type Preview = { latex: string | null; error: string | null };

export function previewExpression(text: string): Preview {
  if (!text.trim()) return { latex: null, error: null };
  try {
    return { latex: toLatex(parseExpression(text)), error: null };
  } catch (error) {
    if (!(error instanceof ExpressionError)) throw error;
    return {
      latex: null,
      error:
        s.expressionErrors[error.code] +
        (error.code === "unexpected" ? s.expressionAt(error.position + 1) : ""),
    };
  }
}

/** Consigne dont la case `\placeholder{}` montre l'expression saisie. */
export function fillPlaceholder(prompt: string, latex: string | null) {
  return prompt.replace(PLACEHOLDER_RE, () => `\\boxed{${latex ?? "\\phantom{x}"}}`);
}

const KEYS: { label: string; insert: string; caret?: number; aria: string }[] = [
  { label: "x", insert: "x", aria: s.formulaKeys.x },
  { label: "x²", insert: "^2", aria: s.formulaKeys.pow2 },
  { label: "xⁿ", insert: "^", aria: s.formulaKeys.pow },
  { label: "√", insert: "sqrt()", caret: 5, aria: s.formulaKeys.sqrt },
  { label: "a/b", insert: "()/()", caret: 1, aria: s.formulaKeys.frac },
  { label: "( )", insert: "()", caret: 1, aria: s.formulaKeys.parens },
  { label: "π", insert: "pi", aria: s.formulaKeys.pi },
];

/** Saisie maison : champ texte + touches, aperçu KaTeX en direct dans la consigne. */
function SimpleField({ value, onChange, disabled, describedBy }: FieldProps) {
  const input = useRef<HTMLInputElement>(null);
  const insert = (text: string, caret = text.length) => {
    const field = input.current;
    const start = field?.selectionStart ?? value.length;
    const end = field?.selectionEnd ?? value.length;
    onChange(value.slice(0, start) + text + value.slice(end));
    requestAnimationFrame(() => {
      field?.focus();
      field?.setSelectionRange(start + caret, start + caret);
    });
  };
  const erase = () => {
    const field = input.current;
    const start = field?.selectionStart ?? value.length;
    const end = field?.selectionEnd ?? value.length;
    const from = start === end ? Math.max(0, start - 1) : start;
    onChange(value.slice(0, from) + value.slice(end));
    requestAnimationFrame(() => {
      field?.focus();
      field?.setSelectionRange(from, from);
    });
  };
  return (
    <div className="flex flex-col gap-2">
      <Input
        ref={input}
        aria-label={s.formula}
        aria-describedby={describedBy}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        autoComplete="off"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        className="font-mono text-lg"
      />
      <div role="group" aria-label={s.formulaKeypad} className="grid grid-cols-4 gap-1.5 sm:grid-cols-8">
        {KEYS.map((key) => (
          <button
            key={key.label}
            type="button"
            aria-label={key.aria}
            disabled={disabled}
            onClick={() => insert(key.insert, key.caret)}
            className="min-h-touch border-border bg-surface hover:bg-surface-2 rounded-lg border font-serif text-lg"
          >
            {key.label}
          </button>
        ))}
        <button
          type="button"
          aria-label={s.formulaKeys.erase}
          disabled={disabled}
          onClick={erase}
          className="min-h-touch border-border bg-surface-2 hover:bg-border rounded-lg border text-lg"
        >
          ⌫
        </button>
      </div>
    </div>
  );
}

export type FieldProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  describedBy?: string;
};

export const formulaInput: ActivityDefinition<ActivityOf<"formula_input">, FormulaResponse> = {
  ownsPrompt: true,
  isComplete: (_a, value) => Boolean(value && previewExpression(value.expression).latex),
  serialize: (value) => ({ expression: normalizeExpression(value.expression).trim() }),
  Renderer({ activity, value, onChange, disabled }) {
    const { formulaInput: mode } = useActivitySettings();
    const text = value?.expression ?? "";
    const preview = useMemo(() => previewExpression(text), [text]);
    const hintId = useId();
    const errorId = useId();
    const field: FieldProps = {
      value: text,
      onChange: (expression) => onChange({ expression }),
      disabled,
      describedBy: cn(hintId, preview.error && errorId),
    };
    return (
      <div className="flex flex-col gap-4">
        <p className="text-lg leading-relaxed">
          <RichText text={fillPlaceholder(activity.prompt, preview.latex)} />
        </p>
        {mode === "mathlive" ? (
          <Suspense fallback={<Spinner label={s.formulaLoading} />}>
            <MathLiveField {...field} />
          </Suspense>
        ) : (
          <SimpleField {...field} />
        )}
        <p id={hintId} className="text-muted text-sm">
          {s.formulaHint}
        </p>
        {preview.error ? (
          <p id={errorId} aria-live="polite" className="text-danger text-sm font-medium">
            {preview.error}
          </p>
        ) : null}
      </div>
    );
  },
};
