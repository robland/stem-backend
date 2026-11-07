import { ingestionKeys, useExerciseLive, useGenerate, type ExerciseDetail } from "@stem/api-client";
import { parsePublicContent } from "@stem/content-schema";
import { Alert, Button, Card, Spinner } from "@stem/ui";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Lightbulb } from "lucide-react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { errorMessage } from "@/lib/errors";
import { quotaAwareMessage } from "@/lib/quota";
import { paths } from "@/paths";
import { t } from "@/strings/fr";
import { Reader } from "./reader/Reader";

/** Parcours : préparation suivie en direct, puis le lecteur. */
export function ExercisePage() {
  const { exerciseId = "" } = useParams();
  const [search] = useSearchParams();
  const extractedId = search.get("enonce");
  const exercise = useExerciseLive(exerciseId);

  if (exercise.isError)
    return (
      <Padded>
        <Alert>{errorMessage(exercise.error)}</Alert>
      </Padded>
    );
  const data = exercise.data;
  if (!data || data.generation_status === "pending" || data.generation_status === "generating")
    return (
      <Padded>
        <Preparing />
      </Padded>
    );
  if (data.generation_status === "ready") {
    const content = parsePublicContent(data.content);
    if (content.ok) return <Reader exercise={data} content={content.data} />;
    return (
      <Padded>
        <Alert>{t.reader.invalidContent}</Alert>
      </Padded>
    );
  }
  return (
    <Padded>
      <Failed exercise={data} extractedId={extractedId} />
    </Padded>
  );
}

const Padded = ({ children }: { children: ReactNode }) => <div className="px-4 py-6">{children}</div>;

function Preparing() {
  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 py-6">
      <div role="status" className="flex flex-col items-center gap-3 text-center">
        <Spinner className="text-primary size-12" />
        <h1 className="text-2xl font-bold">{t.exercise.preparing}</h1>
        <p className="text-muted">{t.exercise.preparingHint}</p>
      </div>
      <Card>
        <ol aria-label={t.exercise.stepsLabel} className="flex flex-col gap-3">
          <li className="flex items-center gap-3">
            <span className="bg-success-soft flex size-7 items-center justify-center rounded-full">
              <Check aria-hidden className="text-success size-4" strokeWidth={3} />
            </span>
            {t.exercise.steps.read}
          </li>
          <li className="flex items-center gap-3 font-semibold">
            <Spinner className="text-primary size-7" />
            {t.exercise.steps.build}
          </li>
        </ol>
      </Card>
      <div className="bg-accent-soft flex gap-3 rounded-xl p-4">
        <Lightbulb aria-hidden className="text-accent size-6 shrink-0" />
        <p className="text-sm">{t.exercise.promise}</p>
      </div>
      <Button asChild variant="ghost">
        <Link to={paths.home}>{t.exercise.backHome}</Link>
      </Button>
    </div>
  );
}

function Failed({ exercise, extractedId }: { exercise: ExerciseDetail; extractedId: string | null }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const generate = useGenerate();

  const relaunch = () => {
    if (!extractedId) return;
    generate.mutate(extractedId, {
      onSuccess: (created) => {
        if (created.id === exercise.id) {
          // Même parcours relancé : le suivi en direct reprend dès que le statut n'est plus final.
          queryClient.setQueryData<ExerciseDetail>(
            ingestionKeys.exercise(exercise.id),
            (old) => old && { ...old, ...created },
          );
        } else {
          navigate(paths.exercise(created.id, { enonce: extractedId }), { replace: true });
        }
      },
    });
  };

  const review = exercise.generation_status === "needs_review";
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{exercise.title || t.exercise.error}</h1>
      <Alert tone={review ? "info" : "danger"}>
        {review ? t.exercise.needsReview : exercise.error_message || t.exercise.error}
      </Alert>
      {generate.error ? <Alert>{quotaAwareMessage(generate.error)}</Alert> : null}
      {!review && extractedId ? (
        <Button size="lg" onClick={relaunch} loading={generate.isPending}>
          {t.exercise.relaunch}
        </Button>
      ) : null}
      <Button asChild variant="secondary" size="lg">
        <Link to={paths.home}>{t.exercise.backHome}</Link>
      </Button>
    </div>
  );
}
