import { cn, Input } from "@stem/ui";
import { Fragment, useId, useState } from "react";
import { shuffle } from "../random";
import { RichText } from "../RichText";
import { s } from "../strings";
import type { ActivityDefinition, ActivityOf, GradingDetails } from "../types";

/** Résultat d'un élément d'après `details` : true, false ou inconnu. */
export function mark(details: GradingDetails | undefined, group: string, key: string): boolean | undefined {
  const value = (details?.[group] as Record<string, unknown> | undefined)?.[key];
  return typeof value === "boolean" ? value : undefined;
}

export const markClass = (ok: boolean | undefined) =>
  ok === true ? "border-success bg-success-soft" : ok === false ? "border-danger bg-danger-soft" : "";

const choiceClass = (selected: boolean) =>
  cn(
    "flex min-h-12 w-full items-center gap-3 rounded-lg border-2 px-4 py-2 text-left text-base transition-colors",
    "disabled:cursor-default",
    selected ? "border-primary bg-primary-soft" : "border-border bg-surface hover:bg-surface-2",
  );

// --- QCM -----------------------------------------------------------------------------------------

type McqResponse = { option_ids: string[] };

export const mcq: ActivityDefinition<ActivityOf<"mcq">, McqResponse> = {
  isComplete: (_a, value) => Boolean(value?.option_ids.length),
  Renderer({ activity, value, onChange, disabled }) {
    const chosen = value?.option_ids ?? [];
    const name = useId();
    const toggle = (id: string) =>
      onChange({
        option_ids: activity.multiple
          ? chosen.includes(id)
            ? chosen.filter((x) => x !== id)
            : [...chosen, id]
          : [id],
      });
    return (
      <fieldset className="flex flex-col gap-2" disabled={disabled}>
        <legend className="sr-only">{s.answer}</legend>
        {activity.options.map((option) => (
          <label
            key={option.id}
            className={cn(
              choiceClass(chosen.includes(option.id)),
              "has-[:focus-visible]:outline-ring cursor-pointer has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px]",
            )}
          >
            <input
              type={activity.multiple ? "checkbox" : "radio"}
              name={name}
              checked={chosen.includes(option.id)}
              onChange={() => toggle(option.id)}
              className="size-5 shrink-0 accent-[rgb(var(--primary))]"
            />
            <RichText text={option.content} />
          </label>
        ))}
      </fieldset>
    );
  },
};

// --- Vrai / faux ---------------------------------------------------------------------------------

type TrueFalseResponse = { value: boolean };

export const trueFalse: ActivityDefinition<ActivityOf<"true_false">, TrueFalseResponse> = {
  isComplete: (_a, value) => value !== undefined,
  Renderer({ value, onChange, disabled }) {
    return (
      <div role="radiogroup" aria-label={s.answer} className="grid grid-cols-2 gap-3">
        {[true, false].map((choice) => (
          <button
            key={String(choice)}
            type="button"
            role="radio"
            aria-checked={value?.value === choice}
            disabled={disabled}
            onClick={() => onChange({ value: choice })}
            className={cn(choiceClass(value?.value === choice), "justify-center text-lg font-semibold")}
          >
            {choice ? s.true : s.false}
          </button>
        ))}
      </div>
    );
  },
};

// --- Réponse courte ------------------------------------------------------------------------------

type TextResponse = { text: string };

export const shortAnswer: ActivityDefinition<ActivityOf<"short_answer">, TextResponse> = {
  isComplete: (_a, value) => Boolean(value?.text.trim()),
  Renderer({ activity, value, onChange, disabled }) {
    const id = useId();
    const numeric = activity.grading === "numeric";
    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={id} className="text-sm font-semibold">
          {s.answer}
        </label>
        <Input
          id={id}
          value={value?.text ?? ""}
          onChange={(e) => onChange({ text: e.target.value })}
          disabled={disabled}
          inputMode={numeric ? "decimal" : "text"}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-describedby={numeric ? `${id}-hint` : undefined}
          className="text-lg"
        />
        {numeric ? (
          <p id={`${id}-hint`} className="text-muted text-sm">
            {s.numberHint}
          </p>
        ) : null}
      </div>
    );
  },
};

// --- Texte à trous -------------------------------------------------------------------------------

type BlanksResponse = { blanks: { id: string; text: string }[] };
const BLANK_RE = /\{\{(\w+)\}\}/g;

export const blankIds = (text: string) => [...text.matchAll(BLANK_RE)].map((m) => m[1]!);

export const fillBlanks: ActivityDefinition<ActivityOf<"fill_blanks">, BlanksResponse> = {
  initial: (activity) => ({ blanks: blankIds(activity.text).map((id) => ({ id, text: "" })) }),
  isComplete: (_a, value) => Boolean(value?.blanks.length && value.blanks.every((b) => b.text.trim())),
  Renderer({ activity, value, onChange, disabled, details }) {
    const parts = activity.text.split(BLANK_RE); // [texte, id, texte, id, …]
    const textOf = (id: string) => value?.blanks.find((b) => b.id === id)?.text ?? "";
    const set = (id: string, text: string) =>
      onChange({
        blanks: blankIds(activity.text).map((b) => ({ id: b, text: b === id ? text : textOf(b) })),
      });
    return (
      <p className="text-lg leading-[2.6]">
        {parts.map((part, i) =>
          i % 2 === 0 ? (
            <RichText key={i} text={part} />
          ) : (
            <Input
              key={i}
              aria-label={s.blank(part)}
              value={textOf(part)}
              onChange={(e) => set(part, e.target.value)}
              disabled={disabled}
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              aria-invalid={mark(details, "blanks", part) === false || undefined}
              className={cn(
                "mx-1 inline-block w-28 border-2 px-2 align-middle",
                markClass(mark(details, "blanks", part)),
              )}
            />
          ),
        )}
      </p>
    );
  },
};

// --- Appariement ---------------------------------------------------------------------------------

type PairsResponse = { pairs: { left_id: string; right_id: string }[] };

/** Toucher un élément de gauche, puis sa correspondance : pas de glisser-déposer (petits écrans, clavier). */
export const matching: ActivityDefinition<ActivityOf<"matching">, PairsResponse> = {
  isComplete: (activity, value) => (value?.pairs.length ?? 0) === activity.left.length,
  Renderer({ activity, value, onChange, disabled, details, seed }) {
    const [active, setActive] = useState<string | null>(activity.left[0]?.id ?? null);
    const pairs = value?.pairs ?? [];
    const right = shuffle(activity.right, seed);
    const rightOf = (leftId: string) => pairs.find((p) => p.left_id === leftId)?.right_id;
    const numberOf = (rightId: string) => right.findIndex((r) => r.id === rightId) + 1;

    const assign = (rightId: string) => {
      if (!active) return;
      const next = [...pairs.filter((p) => p.left_id !== active), { left_id: active, right_id: rightId }];
      onChange({ pairs: next });
      const free = activity.left.find((l) => !next.some((p) => p.left_id === l.id));
      setActive(free?.id ?? null);
    };

    return (
      <div className="flex flex-col gap-4">
        <p className="text-muted text-sm">{s.matchingHint}</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <ul aria-label={s.matchingLeft} className="flex flex-col gap-2">
            {activity.left.map((item) => {
              const chosen = rightOf(item.id);
              const ok = mark(details, "pairs", item.id);
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    disabled={disabled}
                    aria-pressed={active === item.id}
                    onClick={() => setActive(item.id)}
                    className={cn(choiceClass(active === item.id), markClass(ok), "justify-between")}
                  >
                    <RichText text={item.content} />
                    <span className="bg-surface-2 shrink-0 rounded-full px-2.5 py-0.5 text-sm font-bold">
                      {chosen ? (
                        <span aria-label={s.matchingWith(numberOf(chosen))}>→ {numberOf(chosen)}</span>
                      ) : (
                        "?"
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <ul aria-label={s.matchingRight} className="flex flex-col gap-2">
            {right.map((item, i) => (
              <li key={item.id}>
                <button
                  type="button"
                  disabled={disabled || !active}
                  onClick={() => assign(item.id)}
                  className={cn(choiceClass(active !== null && rightOf(active) === item.id), "gap-3")}
                >
                  <span className="bg-primary text-primary-fg flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-bold">
                    {i + 1}
                  </span>
                  <RichText text={item.content} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  },
};

// --- Classement ----------------------------------------------------------------------------------

type OrderResponse = { order: string[] };

export const ordering: ActivityDefinition<ActivityOf<"ordering">, OrderResponse> = {
  initial: (activity, seed) => ({
    order: shuffle(
      activity.items.map((i) => i.id),
      seed,
    ),
  }),
  isComplete: (activity, value) => value?.order.length === activity.items.length,
  Renderer({ activity, value, onChange, disabled }) {
    const order = value?.order ?? activity.items.map((i) => i.id);
    const move = (index: number, delta: number) => {
      const next = [...order];
      const [item] = next.splice(index, 1);
      next.splice(index + delta, 0, item!);
      onChange({ order: next });
    };
    return (
      <div className="flex flex-col gap-2">
        <p className="text-muted text-sm">{s.orderingHint}</p>
        <ol className="flex flex-col gap-2">
          {order.map((id, index) => {
            const item = activity.items.find((i) => i.id === id);
            return (
              <li
                key={id}
                className="border-border bg-surface flex items-center gap-2 rounded-lg border-2 p-2"
              >
                <span
                  aria-label={s.position(index + 1, order.length)}
                  className="bg-surface-2 flex size-8 shrink-0 items-center justify-center rounded-full font-bold"
                >
                  {index + 1}
                </span>
                <span className="grow">{item ? <RichText text={item.content} /> : id}</span>
                {(
                  [
                    [-1, "↑", s.moveUp(index + 1)],
                    [1, "↓", s.moveDown(index + 1)],
                  ] as const
                ).map(([delta, arrow, label]) => (
                  <Fragment key={delta}>
                    <button
                      type="button"
                      aria-label={label}
                      disabled={disabled || index + delta < 0 || index + delta >= order.length}
                      onClick={() => move(index, delta)}
                      className="min-h-touch min-w-touch border-border hover:bg-surface-2 flex items-center justify-center rounded-lg border text-lg font-bold disabled:opacity-30"
                    >
                      {arrow}
                    </button>
                  </Fragment>
                ))}
              </li>
            );
          })}
        </ol>
      </div>
    );
  },
};
