import { ActivityView, initialAnswer, isAnswerComplete, RichText, serializeAnswer } from "@stem/activities";
import { useHint, useSubmitAnswer, type AnswerResult, type StepState } from "@stem/api-client";
import { parseActivity, type StepPublic } from "@stem/content-schema";
import { Alert, Button, cn } from "@stem/ui";
import { CircleAlert, CircleCheck, Lightbulb } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { SpeakButton } from "@/components/SpeakButton";
import { newId } from "@/lib/attempts";
import { errorMessage } from "@/lib/errors";
import { t } from "@/strings/fr";

// Contrat : exactement 3 indices et 3 erreurs au plus par étape (backend README §5.2).
const TOTAL_HINTS = 3;
const MAX_WRONG = 3;

type Props = {
  attemptId: string;
  step: StepPublic;
  state: StepState | undefined;
  isLast: boolean;
  onNext: () => void;
};

export function StepScreen({ attemptId, step, state, isLast, onNext }: Props) {
  const submit = useSubmitAnswer(attemptId);
  const hint = useHint(attemptId);
  const activity = parseActivity(step.activity);
  const [value, setValue] = useState<unknown>(() =>
    activity.ok ? initialAnswer(activity.data, step.id) : undefined,
  );
  const [result, setResult] = useState<AnswerResult | null>(null);
  // Textes des indices déjà obtenus : les 2 premiers sont dans le contenu public, le 3ᵉ vient de l'API.
  const [fetched, setFetched] = useState<Record<number, string>>({});
  // Après une erreur, la même réponse ne se renvoie pas : il faut d'abord la modifier.
  const [dirty, setDirty] = useState(true);
  const pendingUuid = useRef<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => heading.current?.focus(), [step.id]);

  const hintsUsed = state?.hints_used ?? 0;
  const status = result?.step.status ?? state?.status ?? "pending";
  const closed = status !== "pending";
  const wrongAnswers = result?.step.wrong_answers ?? state?.wrong_answers ?? 0;
  const unchanged = result !== null && !result.is_correct && !dirty;
  const complete = activity.ok && isAnswerComplete(activity.data, value);

  const change = (next: unknown) => {
    setValue(next);
    setDirty(true);
    pendingUuid.current = null;
    if (result && !result.is_correct) setResult({ ...result, details: {} });
  };

  const check = () => {
    if (!activity.ok) return;
    // Même identifiant si on renvoie après une coupure : le serveur ne compte pas deux fois.
    pendingUuid.current ??= newId();
    submit.mutate(
      { step_id: step.id, response: serializeAnswer(activity.data, value), client_uuid: pendingUuid.current },
      {
        onSuccess: (answer) => {
          setResult(answer);
          setDirty(false);
          pendingUuid.current = null;
        },
      },
    );
  };

  const askHint = () =>
    hint.mutate(step.id, { onSuccess: (h) => setFetched((f) => ({ ...f, [h.level]: h.hint })) });

  const hints = Array.from({ length: hintsUsed }, (_, i) => fetched[i + 1] ?? step.hints[i] ?? null);

  return (
    <div className="flex grow flex-col">
      <div className="flex grow flex-col gap-5 px-4 py-5">
        <div className="flex items-center justify-between gap-2">
          <h1
            ref={heading}
            tabIndex={-1}
            className="text-primary text-sm font-bold uppercase tracking-wide outline-none"
          >
            <RichText text={step.objective} />
          </h1>
          {activity.ok ? <SpeakButton text={activity.data.prompt} /> : null}
        </div>

        <ActivityView
          activity={step.activity}
          value={value}
          onChange={change}
          disabled={closed || submit.isPending}
          details={result?.details ?? null}
          seed={step.id}
        />

        {hints.length ? (
          <ol className="flex flex-col gap-2" aria-label={t.reader.hint(hintsUsed)}>
            {hints.map((text, i) => (
              <li key={i} className="bg-accent-soft rounded-xl p-4">
                <p className="text-sm font-bold">{t.reader.hintTitle(i + 1, TOTAL_HINTS)}</p>
                <p className="mt-1">
                  {text ? (
                    <RichText text={text} />
                  ) : (
                    <span className="text-muted">{t.reader.hintAlreadySeen}</span>
                  )}
                </p>
              </li>
            ))}
          </ol>
        ) : null}

        <Feedback result={result} status={status} wrongAnswers={wrongAnswers} />
        {submit.error ? <Alert>{errorMessage(submit.error)}</Alert> : null}
        {hint.error ? <Alert>{errorMessage(hint.error)}</Alert> : null}
      </div>

      <div className="border-border bg-surface sticky bottom-0 flex gap-3 border-t px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3">
        {closed ? (
          <Button size="lg" block onClick={onNext}>
            {isLast ? t.reader.seeSummary : t.reader.nextStep}
          </Button>
        ) : (
          <>
            <Button
              variant="secondary"
              size="lg"
              onClick={askHint}
              loading={hint.isPending}
              disabled={hintsUsed >= TOTAL_HINTS || submit.isPending}
              className="border-accent flex-col gap-0 border-2 leading-tight"
            >
              <span className="flex items-center gap-1.5">
                <Lightbulb aria-hidden className="text-accent size-5" />
                {hintsUsed >= TOTAL_HINTS ? t.reader.noMoreHints : t.reader.hint(hintsUsed + 1)}
              </span>
              {hintsUsed < TOTAL_HINTS ? (
                <span className="text-muted text-xs font-normal">{t.reader.hintCost}</span>
              ) : null}
            </Button>
            <Button
              size="lg"
              className="grow"
              onClick={check}
              loading={submit.isPending}
              disabled={!complete || unchanged}
            >
              {submit.isPending
                ? t.reader.sending
                : result && !result.is_correct
                  ? t.reader.retry
                  : t.reader.check}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function Feedback({
  result,
  status,
  wrongAnswers,
}: {
  result: AnswerResult | null;
  status: string;
  wrongAnswers: number;
}) {
  if (!result) return null;
  const success = result.is_correct;
  const failed = status === "failed";
  return (
    <div
      role={success ? "status" : "alert"}
      className={cn(
        "motion-safe:animate-pop flex flex-col gap-2 rounded-xl border p-4",
        success ? "border-success/40 bg-success-soft" : "border-danger/40 bg-danger-soft",
      )}
    >
      <p className={cn("flex items-center gap-2 font-bold", success ? "text-success" : "text-danger")}>
        {success ? (
          <CircleCheck aria-hidden className="size-5" />
        ) : (
          <CircleAlert aria-hidden className="size-5" />
        )}
        {success ? t.reader.correctAfter(wrongAnswers) : failed ? t.reader.failed : t.reader.wrong}
      </p>
      {!success && result.feedback ? (
        <p>
          <RichText text={result.feedback} />
        </p>
      ) : null}
      {!success && !failed ? (
        <p className="text-muted text-sm">{t.reader.triesLeft(MAX_WRONG - wrongAnswers)}</p>
      ) : null}
      {result.explanation ? (
        <div className="bg-surface mt-1 rounded-lg p-3">
          <p className="text-sm font-bold">{t.reader.explanation}</p>
          <p className="mt-1">
            <RichText text={result.explanation} />
          </p>
        </div>
      ) : null}
    </div>
  );
}
