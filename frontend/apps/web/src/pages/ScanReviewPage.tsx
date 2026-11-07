import { RichText } from "@stem/activities";
import {
  isApiError,
  useChapters,
  useDiscardExtracted,
  useGenerate,
  useMe,
  useUpdateExtracted,
  useUpload,
  useValidateExtracted,
  type ExtractedExercise,
  type ExtractedExercisePatch,
  type Level,
  type SubjectCode,
} from "@stem/api-client";
import { Alert, Button, Card, cn, Field, Select, Spinner } from "@stem/ui";
import { ArrowLeft } from "lucide-react";
import { useDeferredValue, useId, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { errorMessage } from "@/lib/errors";
import { getPhoto } from "@/lib/localPhotos";
import { quotaAwareMessage } from "@/lib/quota";
import { paths } from "@/paths";
import { LEVELS, SUBJECTS, t } from "@/strings/fr";

const isOpen = (subject: SubjectCode | null) => SUBJECTS.some((s) => s.value === subject && s.available);

export function ScanReviewPage() {
  const { uploadId = "" } = useParams();
  const upload = useUpload(uploadId);
  const [selected, setSelected] = useState(0);

  const header = (title: string) => (
    <div className="mb-5 flex items-center gap-2">
      <Button asChild variant="ghost" size="icon">
        <Link to={paths.scan} aria-label={t.common.back}>
          <ArrowLeft aria-hidden className="size-5" />
        </Link>
      </Button>
      <h1 className="text-2xl font-bold">{title}</h1>
    </div>
  );

  if (upload.isError) {
    return (
      <>
        {header(t.scan.title)}
        <Alert>{errorMessage(upload.error)}</Alert>
      </>
    );
  }

  const data = upload.data;
  if (!data || data.status === "pending" || data.status === "reading") {
    return (
      <>
        {header(t.scan.title)}
        <Card role="status" className="flex flex-col items-center gap-3 py-10 text-center">
          <Spinner className="text-primary size-8" />
          <p className="text-lg font-semibold">{t.scan.reading}</p>
          <p className="text-muted">{t.scan.readingHint}</p>
        </Card>
      </>
    );
  }

  if (data.status === "error") {
    return (
      <>
        {header(t.scan.title)}
        <div className="flex flex-col gap-4">
          <Alert>
            <p className="font-semibold">{t.scan.readError}</p>
            {data.error_message ? <p className="mt-1">{data.error_message}</p> : null}
          </Alert>
          <Button asChild size="lg">
            <Link to={paths.scan}>{t.scan.retry}</Link>
          </Button>
        </div>
      </>
    );
  }

  const exercises = [...data.exercises].sort((a, b) => a.order - b.order);
  if (exercises.length === 0) {
    return (
      <>
        {header(t.scan.title)}
        <div className="flex flex-col gap-4">
          <Alert tone="info">{t.scan.noneFound}</Alert>
          <Button asChild size="lg">
            <Link to={paths.scan}>{t.scan.newScan}</Link>
          </Button>
        </div>
      </>
    );
  }

  const index = Math.min(selected, exercises.length - 1);
  const current = exercises[index]!;

  return (
    <>
      {header(t.scan.found(exercises.length))}
      <div className="flex flex-col gap-5">
        {exercises.length > 1 ? (
          <div role="tablist" aria-label={t.scan.exercisesTabs} className="flex gap-2 overflow-x-auto pb-1">
            {exercises.map((exercise, i) => (
              <button
                key={exercise.id}
                type="button"
                role="tab"
                id={`tab-${exercise.id}`}
                aria-selected={i === index}
                aria-controls="exercise-panel"
                onClick={() => setSelected(i)}
                className={cn(
                  "min-h-touch shrink-0 rounded-full border-2 px-4 font-semibold",
                  i === index ? "border-primary bg-primary-soft" : "border-border bg-surface",
                )}
              >
                {t.scan.exerciseTab(i + 1)}
                {exercise.validated_at ? " ✓" : ""}
              </button>
            ))}
          </div>
        ) : null}
        <div
          id="exercise-panel"
          role={exercises.length > 1 ? "tabpanel" : undefined}
          aria-labelledby={exercises.length > 1 ? `tab-${current.id}` : undefined}
        >
          <ExerciseEditor
            key={current.id}
            uploadId={uploadId}
            exercise={current}
            photo={getPhoto(uploadId)}
          />
        </div>
      </div>
    </>
  );
}

function ExerciseEditor({
  uploadId,
  exercise,
  photo,
}: {
  uploadId: string;
  exercise: ExtractedExercise;
  photo: string | null;
}) {
  const navigate = useNavigate();
  const me = useMe();
  const update = useUpdateExtracted(uploadId);
  const validate = useValidateExtracted(uploadId);
  const generate = useGenerate();
  const discard = useDiscardExtracted(uploadId);
  const statementId = useId();

  const [statement, setStatement] = useState(exercise.statement);
  const [subject, setSubject] = useState<SubjectCode | null>(exercise.subject ?? null);
  const [level, setLevel] = useState<Level | "">(exercise.level || me.data?.level || "");
  const [chapter, setChapter] = useState<string | null>(exercise.chapter ?? null);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const deferredStatement = useDeferredValue(statement);
  const chapters = useChapters(subject ?? undefined, level || undefined);

  const locked = Boolean(exercise.validated_at);
  const busy = update.isPending || validate.isPending || generate.isPending;
  const fieldErrors = isApiError(update.error) ? update.error.fieldErrors : {};

  const start = async () => {
    setProblem(null);
    if (!subject) return setProblem(t.scan.subjectMissing);
    if (!level) return setProblem(t.scan.levelMissing);
    if (!locked) {
      const patch: ExtractedExercisePatch = {};
      if (statement !== exercise.statement) patch.statement = statement;
      if (subject !== (exercise.subject ?? null)) patch.subject = subject;
      if (level !== exercise.level) patch.level = level;
      if (chapter !== (exercise.chapter ?? null)) patch.chapter = chapter;
      if (Object.keys(patch).length) {
        try {
          await update.mutateAsync({ id: exercise.id, patch });
        } catch (error) {
          // Les erreurs par champ s'affichent sous les champs.
          if (!(isApiError(error) && Object.keys(error.fieldErrors).length)) setProblem(errorMessage(error));
          return;
        }
      }
    }
    try {
      if (!locked) await validate.mutateAsync(exercise.id);
      const created = await generate.mutateAsync(exercise.id);
      navigate(paths.exercise(created.id, exercise.id));
    } catch (error) {
      setProblem(quotaAwareMessage(error));
    }
  };

  const onDiscard = () => {
    if (window.confirm(t.scan.discardConfirm)) {
      discard.mutate(exercise.id, { onError: (error) => setProblem(errorMessage(error)) });
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start gap-3">
        {photo ? (
          <button
            type="button"
            onClick={() => setPhotoOpen((open) => !open)}
            aria-expanded={photoOpen}
            aria-label={t.scan.yourPhoto}
            className={cn(
              "border-border bg-surface-2 shrink-0 overflow-hidden rounded-lg border transition-[width]",
              photoOpen ? "w-full" : "w-24",
            )}
          >
            <img src={photo} alt="" className="block h-auto w-full" />
          </button>
        ) : null}
        {!photoOpen ? (
          <div className="flex flex-col gap-1">
            <p className="font-bold">{t.scan.checkTitle}</p>
            <p className="text-muted text-sm">{t.scan.checkHint}</p>
          </div>
        ) : null}
      </div>

      {locked ? <Alert tone="info">{t.scan.validated}</Alert> : null}

      <Field label={t.scan.statement} hint={t.scan.statementHint} error={fieldErrors.statement}>
        {({ id, describedBy, invalid }) => (
          <textarea
            id={id}
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            readOnly={locked}
            aria-describedby={`${describedBy ?? ""} ${statementId}`.trim()}
            aria-invalid={invalid}
            rows={5}
            maxLength={5000}
            spellCheck={false}
            className="border-border bg-surface aria-[invalid=true]:border-danger min-h-32 w-full rounded-lg border p-3 font-mono text-[15px] leading-relaxed"
          />
        )}
      </Field>

      <section aria-labelledby={statementId} className="flex flex-col gap-1.5">
        <h2 id={statementId} className="text-sm font-semibold">
          {t.scan.preview}
        </h2>
        <div
          aria-live="polite"
          className="border-border bg-surface rounded-lg border border-dashed p-3 text-base leading-relaxed"
        >
          <RichText text={deferredStatement} />
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t.scan.subject} error={fieldErrors.subject}>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={subject ?? ""}
              disabled={locked}
              aria-invalid={invalid}
              onChange={(e) => {
                setSubject((e.target.value || null) as SubjectCode | null);
                setChapter(null);
              }}
            >
              <option value="">—</option>
              {SUBJECTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.available ? s.label : t.scan.subjectSoon(s.label)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t.scan.level} error={fieldErrors.level}>
          {({ id, invalid }) => (
            <Select
              id={id}
              value={level}
              disabled={locked}
              aria-invalid={invalid}
              onChange={(e) => {
                setLevel(e.target.value as Level | "");
                setChapter(null);
              }}
            >
              <option value="">—</option>
              {LEVELS.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      {chapters.data?.length ? (
        <Field
          label={t.scan.chapter}
          hint={exercise.chapter_hint ? t.scan.chapterHint(exercise.chapter_hint) : undefined}
          error={fieldErrors.chapter}
        >
          {({ id, describedBy, invalid }) => (
            <Select
              id={id}
              value={chapter ?? ""}
              disabled={locked}
              aria-describedby={describedBy}
              aria-invalid={invalid}
              onChange={(e) => setChapter(e.target.value || null)}
            >
              <option value="">{t.scan.chapterNone}</option>
              {chapters.data.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      ) : exercise.chapter_hint ? (
        <p className="text-muted text-sm">{t.scan.chapterHint(exercise.chapter_hint)}</p>
      ) : null}

      {subject && !isOpen(subject) ? <Alert tone="info">{t.scan.subjectNotOpen}</Alert> : null}
      {problem ? <Alert>{problem}</Alert> : null}

      <div className="flex gap-3">
        {!locked ? (
          <Button
            variant="secondary"
            size="lg"
            onClick={onDiscard}
            loading={discard.isPending}
            disabled={busy}
          >
            {t.scan.discard}
          </Button>
        ) : null}
        <Button
          size="lg"
          className="grow"
          onClick={start}
          loading={busy}
          disabled={!isOpen(subject) || !statement.trim()}
        >
          {locked ? t.scan.open : t.scan.go}
        </Button>
      </div>
    </div>
  );
}
