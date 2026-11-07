import { RichText } from "@stem/activities";
import type { Attempt } from "@stem/api-client";
import type { ExerciseContentPublic } from "@stem/content-schema";
import { Button, Card, cn } from "@stem/ui";
import { Check, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

type Props = { content: ExerciseContentPublic; attempt: Attempt; onRedo: () => void; redoing: boolean };

export function Summary({ content, attempt, onRedo, redoing }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  return (
    <div className="flex flex-col gap-5 px-4 py-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <div
          role="img"
          aria-label={t.reader.score(attempt.score)}
          className="flex size-32 items-center justify-center rounded-full"
          style={{
            background: `conic-gradient(rgb(var(--primary)) ${attempt.score}%, rgb(var(--surface-2)) 0)`,
          }}
        >
          <div className="bg-bg flex size-24 flex-col items-center justify-center rounded-full">
            <span className="text-3xl font-extrabold leading-none">{attempt.score}</span>
            <span className="text-muted text-xs">/ 100</span>
          </div>
        </div>
        <h1 ref={heading} tabIndex={-1} className="text-2xl font-bold outline-none">
          {t.reader.summaryTitle}
        </h1>
        <p className="text-muted">{content.title}</p>
      </div>

      <Card className="p-0">
        <ul>
          {content.steps.map((step) => {
            const state = attempt.steps.find((s) => s.step_id === step.id);
            const ok = state?.status === "succeeded";
            const details = state ? t.reader.stepDetails(state.hints_used, state.wrong_answers) : "";
            return (
              <li
                key={step.id}
                className="border-border flex items-center gap-3 border-b px-4 py-3 last:border-b-0"
              >
                <span
                  role="img"
                  aria-label={ok ? t.reader.stepSucceeded : t.reader.stepFailed}
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full",
                    ok ? "bg-success-soft text-success" : "bg-danger-soft text-danger",
                  )}
                >
                  {ok ? (
                    <Check aria-hidden className="size-4" strokeWidth={3} />
                  ) : (
                    <X aria-hidden className="size-4" strokeWidth={3} />
                  )}
                </span>
                <span className="grow">
                  <RichText text={step.objective} />
                  {details ? <span className="text-muted block text-xs">{details}</span> : null}
                </span>
                <span className="shrink-0 font-bold">{t.reader.stepScore(state?.score ?? 0)}</span>
              </li>
            );
          })}
        </ul>
      </Card>

      <div className="bg-primary-soft flex flex-col gap-1 rounded-xl p-4">
        <p className="text-primary text-sm font-bold uppercase tracking-wide">{t.reader.keyTakeaway}</p>
        <p className="text-lg leading-relaxed">
          <RichText text={content.summary.key_takeaway} />
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <Button size="lg" onClick={onRedo} loading={redoing}>
          {t.reader.redo}
        </Button>
        <Button variant="secondary" disabled>
          {t.reader.challenge}
        </Button>
        <p className="text-muted text-center text-xs">{t.reader.soonNote}</p>
        <Button asChild variant="ghost">
          <Link to={paths.home}>{t.exercise.backHome}</Link>
        </Button>
      </div>
    </div>
  );
}
