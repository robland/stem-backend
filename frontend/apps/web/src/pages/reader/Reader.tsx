import { ActivitySettingsContext, RichText } from "@stem/activities";
import { isApiError, useAttempt, useStartAttempt, type ExerciseDetail } from "@stem/api-client";
import type { ExerciseContentPublic } from "@stem/content-schema";
import { Alert, Button, Card, Spinner } from "@stem/ui";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { SpeakButton } from "@/components/SpeakButton";
import { newId } from "@/lib/attempts";
import { errorMessage } from "@/lib/errors";
import { usePreferences } from "@/lib/preferences";
import { t } from "@/strings/fr";
import { ReaderHeader } from "./ReaderHeader";
import { StepScreen } from "./StepScreen";
import { Summary } from "./Summary";

type Screen =
  | { kind: "intro" }
  | { kind: "intuition" }
  | { kind: "recall" }
  | { kind: "step"; stepId: string }
  | { kind: "summary" };

/**
 * Lecteur de parcours (README frontend §2) : intro → intuition → rappels → une étape par écran → bilan.
 * La tentative vit sur le serveur, qui indique celle à reprendre (`current_attempt`).
 */
export function Reader({ exercise, content }: { exercise: ExerciseDetail; content: ExerciseContentPublic }) {
  const [search] = useSearchParams();
  const prefs = usePreferences();
  // Tentative à reprendre : celle de la révision du jour, sinon `current_attempt` (même sur un autre appareil).
  const [attemptId, setAttemptId] = useState(() => search.get("tentative") ?? exercise.current_attempt);
  const attempt = useAttempt(attemptId);
  const start = useStartAttempt(exercise.id);
  const [screen, setScreen] = useState<Screen>({ kind: "intro" });
  const settings = useMemo(() => ({ formulaInput: prefs.formulaInput }), [prefs.formulaInput]);

  // Tentative introuvable (lien périmé) : on repart de zéro.
  const lost = attempt.isError && isApiError(attempt.error) && attempt.error.status === 404;
  const current = lost ? undefined : attempt.data;
  const unfinished = current && !current.finished_at ? current : null;

  const top = useRef<HTMLDivElement>(null);
  useEffect(() => top.current?.scrollIntoView?.({ block: "start" }), [screen]);

  const begin = () =>
    start.mutate(newId(), {
      onSuccess: (created) => {
        setAttemptId(created.id);
        setScreen({ kind: "intuition" });
      },
    });

  const goToCurrent = (stepId: string | null | undefined) =>
    setScreen(stepId ? { kind: "step", stepId } : { kind: "summary" });

  const firstStep = () => goToCurrent(current?.current_step_id ?? content.steps[0]?.id);

  let body;
  if (attemptId && attempt.isPending) {
    body = <Spinner label={t.common.loading} className="m-8 self-center" />;
  } else if (screen.kind === "intro") {
    body = (
      <div className="flex flex-col gap-5 px-4 py-6">
        <header>
          <p className="text-muted text-sm font-semibold">{t.reader.stepsCount(content.steps.length)}</p>
          <h1 className="text-2xl font-bold">{content.title}</h1>
        </header>
        <Card className="flex items-start gap-2 text-lg leading-relaxed">
          <p className="grow">
            <RichText text={content.statement} />
          </p>
          <SpeakButton text={content.statement} />
        </Card>
        {current?.finished_at ? <p className="text-muted">{t.reader.lastScore(current.score)}</p> : null}
        {start.error ? <Alert>{errorMessage(start.error)}</Alert> : null}
        <div className="flex flex-col gap-3">
          {unfinished ? (
            <>
              <Button size="lg" onClick={() => goToCurrent(unfinished.current_step_id)}>
                {t.reader.resume}
              </Button>
              <Button variant="secondary" size="lg" onClick={begin} loading={start.isPending}>
                {t.reader.restart}
              </Button>
            </>
          ) : (
            <Button size="lg" onClick={begin} loading={start.isPending}>
              {t.reader.start}
            </Button>
          )}
        </div>
      </div>
    );
  } else if (screen.kind === "intuition") {
    body = (
      <Card className="m-4 flex flex-col gap-4">
        <h1 className="text-xl font-bold">{t.reader.intuition}</h1>
        <p className="text-lg leading-relaxed">
          <RichText text={content.intuition.mental_image} />
        </p>
        <div className="bg-surface-2 rounded-lg p-3">
          <p className="text-sm font-bold">{t.reader.example}</p>
          <p className="mt-1">
            <RichText text={content.intuition.example} />
          </p>
        </div>
        <Button
          size="lg"
          onClick={() => (content.recall.length ? setScreen({ kind: "recall" }) : firstStep())}
        >
          {t.reader.next}
        </Button>
      </Card>
    );
  } else if (screen.kind === "recall") {
    body = (
      <div className="flex flex-col gap-3 px-4 py-5">
        <h1 className="text-xl font-bold">{t.reader.recall}</h1>
        {content.recall.map((recall, i) => (
          <Card key={i} className="flex flex-col gap-2">
            <p className="text-primary text-xs font-bold uppercase tracking-wide">
              {t.reader.recallKinds[recall.kind]}
            </p>
            <p className="text-lg">
              <RichText text={recall.content} />
            </p>
            <p className="text-muted">
              <RichText text={recall.explanation} />
            </p>
          </Card>
        ))}
        <Button size="lg" onClick={firstStep}>
          {t.reader.next}
        </Button>
      </div>
    );
  } else if (screen.kind === "step" && current && attemptId) {
    const index = content.steps.findIndex((s) => s.id === screen.stepId);
    const step = content.steps[index];
    body = step ? (
      <StepScreen
        key={step.id}
        attemptId={attemptId}
        step={step}
        state={current.steps.find((s) => s.step_id === step.id)}
        isLast={index === content.steps.length - 1}
        onNext={() => goToCurrent(current.current_step_id)}
      />
    ) : (
      <Alert>{t.reader.invalidContent}</Alert>
    );
  } else if (screen.kind === "summary" && current) {
    body = <Summary content={content} attempt={current} onRedo={begin} redoing={start.isPending} />;
  } else {
    body = (
      <Alert className="m-4">{attempt.error ? errorMessage(attempt.error) : t.reader.invalidContent}</Alert>
    );
  }

  return (
    <ActivitySettingsContext.Provider value={settings}>
      <div ref={top} />
      <ReaderHeader
        statement={content.statement}
        steps={content.steps}
        states={current?.steps ?? []}
        currentId={screen.kind === "step" ? screen.stepId : null}
      />
      <main className="flex grow flex-col" aria-label={exercise.title}>
        {body}
      </main>
    </ActivitySettingsContext.Provider>
  );
}
