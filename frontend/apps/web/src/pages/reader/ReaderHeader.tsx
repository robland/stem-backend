import { RichText } from "@stem/activities";
import type { StepState } from "@stem/api-client";
import { Button, cn } from "@stem/ui";
import { X } from "lucide-react";
import { Link } from "react-router-dom";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

type Props = {
  statement: string;
  steps: { id: string }[];
  states: StepState[];
  /** Étape affichée ; null hors des étapes (intro, bilan). */
  currentId: string | null;
};

/** Quitter, progression par étape (réussie / échouée / en cours) et rappel de l'énoncé. */
export function ReaderHeader({ statement, steps, states, currentId }: Props) {
  const index = steps.findIndex((s) => s.id === currentId);
  const label = index >= 0 ? t.reader.progress(index + 1, steps.length) : t.reader.stepsCount(steps.length);
  return (
    <header className="border-border bg-surface/95 sticky top-0 z-10 flex flex-col gap-1 border-b px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="icon">
          <Link to={paths.home} aria-label={t.reader.quit}>
            <X aria-hidden className="size-5" />
          </Link>
        </Button>
        <div
          role="progressbar"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={steps.length}
          aria-valuenow={Math.max(0, index + 1)}
          className="grid grow gap-1"
          style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}
        >
          {steps.map((step) => {
            const status = states.find((s) => s.step_id === step.id)?.status;
            return (
              <span
                key={step.id}
                className={cn(
                  "h-2 rounded-full",
                  status === "succeeded"
                    ? "bg-success"
                    : status === "failed"
                      ? "bg-danger"
                      : step.id === currentId
                        ? "bg-primary"
                        : "bg-surface-2",
                )}
              />
            );
          })}
        </div>
        <span aria-hidden className="text-muted min-w-10 text-right text-sm font-semibold">
          {index >= 0 ? `${index + 1}/${steps.length}` : ""}
        </span>
      </div>
      <details className="text-muted text-sm">
        <summary className="flex min-h-8 cursor-pointer items-center">{t.reader.statement}</summary>
        <p className="text-fg pb-2 pt-1 text-base">
          <RichText text={statement} />
        </p>
      </details>
    </header>
  );
}
