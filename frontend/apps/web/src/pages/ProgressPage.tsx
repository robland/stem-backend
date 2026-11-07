import {
  useExercises,
  useProgress,
  type Mastery,
  type MasteryState,
  type SubjectCode,
} from "@stem/api-client";
import { Alert, Button, Card, cn, Meter, Spinner } from "@stem/ui";
import { CircleAlert, CircleCheck, CircleDashed, Flame, type LucideIcon } from "lucide-react";
import { forwardRef, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { ReviewList } from "@/components/ReviewList";
import { relativeDay } from "@/lib/dates";
import { errorMessage } from "@/lib/errors";
import { paths } from "@/paths";
import { LEVELS, SUBJECTS, t } from "@/strings/fr";

const subjectLabel = (code: string) => SUBJECTS.find((s) => s.value === code)?.label ?? code;
const levelLabel = (code: string) => LEVELS.find((l) => l.value === code)?.label ?? code;

// États de maîtrise = statuts : couleur réservée, toujours avec icône et libellé (jamais la couleur seule).
const STATES: Record<MasteryState, { icon: LucideIcon; className: string }> = {
  maitrise: { icon: CircleCheck, className: "bg-success-soft text-success" },
  en_cours: { icon: CircleDashed, className: "bg-primary-soft text-primary" },
  non_acquis: { icon: CircleAlert, className: "bg-danger-soft text-danger" },
};

const WEAK_POINTS = 3;

export function ProgressPage() {
  const progress = useProgress();
  const [filter, setFilter] = useState<SubjectCode | null>(null);
  const [chapter, setChapter] = useState<{ id: string; name: string } | null>(null);
  const exercisesSection = useRef<HTMLElement>(null);
  const showChapter = (m: Mastery) => {
    setChapter({ id: m.chapter.id, name: m.chapter.name });
    exercisesSection.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  };

  if (progress.isPending) return <Spinner label={t.common.loading} />;
  if (progress.isError) return <Alert>{errorMessage(progress.error)}</Alert>;

  const { summary, subjects, chapters, review_today } = progress.data;
  const chapterSubjects = [...new Set(chapters.map((m) => m.chapter.subject))];
  const shown = filter ? chapters.filter((m) => m.chapter.subject === filter) : chapters;
  const weak = shown
    .filter((m) => m.state !== "maitrise")
    .sort((a, b) => (a.score ?? 0) - (b.score ?? 0))
    .slice(0, WEAK_POINTS);

  return (
    <>
      <PageHeader title={t.progress.title} />
      <div className="flex flex-col gap-7">
        <section aria-label={t.progress.summary} className="grid grid-cols-3 gap-2 sm:gap-3">
          <StatTile
            value={summary.exercises_done}
            label={t.progress.exercisesDone(summary.exercises_done)}
            detail={t.progress.attempts(summary.attempts_finished)}
          />
          <StatTile value={summary.average_score ?? t.progress.noScore} label={t.progress.averageScore} />
          <StatTile
            value={summary.streak_days}
            label={t.progress.streak(summary.streak_days)}
            icon={Flame}
            highlight
          />
        </section>

        {summary.attempts_finished === 0 ? (
          <Card className="flex flex-col items-start gap-3">
            <p>{t.progress.empty}</p>
            <Button asChild>
              <Link to={paths.scan}>{t.progress.emptyCta}</Link>
            </Button>
          </Card>
        ) : null}

        {review_today.length ? (
          <Section title={t.home.reviewToday}>
            <ReviewList items={review_today} />
          </Section>
        ) : null}

        {subjects.length ? (
          <Section title={t.progress.subjects}>
            <ul className="grid gap-2 sm:grid-cols-2">
              {subjects.map((s) => (
                <li key={s.subject}>
                  <Card className="flex flex-col gap-2">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-semibold">{subjectLabel(s.subject)}</span>
                      <span className="text-muted text-sm">{t.progress.subjectLine(s.exercises_done)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Meter
                        value={s.average_score}
                        label={t.progress.subjectAverage(subjectLabel(s.subject))}
                      />
                      <span className="shrink-0 text-sm font-bold">{s.average_score}/100</span>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          </Section>
        ) : null}

        <Section title={t.progress.chapters}>
          {chapterSubjects.length > 1 ? (
            <div role="group" aria-label={t.progress.subjectFilter} className="flex flex-wrap gap-2">
              {[null, ...chapterSubjects].map((code) => (
                <button
                  key={code ?? "all"}
                  type="button"
                  aria-pressed={filter === code}
                  onClick={() => setFilter(code)}
                  className={cn(
                    "min-h-touch rounded-full border-2 px-4 font-semibold",
                    filter === code ? "border-primary bg-primary-soft" : "border-border bg-surface",
                  )}
                >
                  {code ? subjectLabel(code) : t.progress.allSubjects}
                </button>
              ))}
            </div>
          ) : null}

          {weak.length ? (
            <div className="bg-danger-soft/50 flex flex-col gap-2 rounded-xl p-3">
              <h3 className="font-bold">{t.progress.weakPoints}</h3>
              <p className="text-muted text-sm">{t.progress.weakPointsHint}</p>
              <ul className="flex flex-col gap-2">
                {weak.map((m) => (
                  <li key={m.chapter.id}>
                    <ChapterCard mastery={m} onShow={showChapter} />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {shown.length ? (
            <ul className="flex flex-col gap-2">
              {shown.map((m) => (
                <li key={m.chapter.id}>
                  <ChapterCard mastery={m} onShow={showChapter} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted">{t.progress.chaptersEmpty}</p>
          )}
        </Section>

        <MyExercises ref={exercisesSection} chapter={chapter} onClear={() => setChapter(null)} />
      </div>
    </>
  );
}

const Section = forwardRef<HTMLElement, { title: string; children: ReactNode }>(function Section(
  { title, children },
  ref,
) {
  return (
    <section ref={ref} className="flex scroll-mt-4 flex-col gap-3">
      <h2 className="text-lg font-bold">{title}</h2>
      {children}
    </section>
  );
});

function StatTile({
  value,
  label,
  detail,
  icon: Icon,
  highlight,
}: {
  value: number | string;
  label: string;
  detail?: string;
  icon?: LucideIcon;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-0.5 rounded-xl border p-3",
        highlight ? "bg-accent-soft border-transparent" : "border-border bg-surface",
      )}
    >
      <span className="flex items-center gap-1 text-2xl font-extrabold sm:text-3xl">
        {Icon ? <Icon aria-hidden className="text-accent size-5" /> : null}
        {value}
      </span>
      <span className="text-muted text-xs sm:text-sm">{label}</span>
      {detail ? <span className="text-muted hidden text-xs sm:block">{detail}</span> : null}
    </div>
  );
}

function ChapterCard({ mastery, onShow }: { mastery: Mastery; onShow: (m: Mastery) => void }) {
  const state = mastery.state ?? "non_acquis";
  const { icon: Icon, className } = STATES[state];
  const score = mastery.score ?? 0;
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <span className="font-semibold">{mastery.chapter.name}</span>
        <span
          className={cn(
            "flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold",
            className,
          )}
        >
          <Icon aria-hidden className="size-3.5" />
          {t.progress.states[state]}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <Meter value={score} label={t.progress.masteryLabel(mastery.chapter.name)} />
        <span className="shrink-0 text-sm font-bold">{score}/100</span>
      </div>
      {mastery.next_review_at ? (
        <p className="text-muted text-sm">{t.progress.review(relativeDay(mastery.next_review_at))}</p>
      ) : null}
      <Button variant="ghost" className="text-primary self-start px-0" onClick={() => onShow(mastery)}>
        {t.progress.chapterExercises}
      </Button>
    </Card>
  );
}

type MyExercisesProps = { chapter: { id: string; name: string } | null; onClear: () => void };

/** Mes parcours (tous, ou ceux d'un chapitre choisi dans la maîtrise : `GET exercises?chapter=`). */
const MyExercises = forwardRef<HTMLElement, MyExercisesProps>(function MyExercises(
  { chapter, onClear },
  ref,
) {
  const exercises = useExercises(chapter?.id);
  const items = exercises.data?.pages.flatMap((p) => p.results) ?? [];
  return (
    <Section
      ref={ref}
      title={chapter ? t.progress.chapterExercisesTitle(chapter.name) : t.progress.myExercises}
    >
      {chapter ? (
        <Button variant="secondary" className="self-start" onClick={onClear}>
          {t.progress.allExercises}
        </Button>
      ) : null}
      {exercises.isPending ? <Spinner label={t.common.loading} /> : null}
      {exercises.isError ? <Alert>{errorMessage(exercises.error)}</Alert> : null}
      {exercises.isSuccess && !items.length ? (
        <p className="text-muted">{t.progress.myExercisesEmpty}</p>
      ) : null}
      <ul className="flex flex-col gap-2">
        {items.map((e) => (
          <li key={e.id}>
            <Link
              to={paths.exercise(e.id)}
              className="min-h-touch border-border bg-surface hover:bg-surface-2 flex items-center justify-between gap-3 rounded-xl border p-4"
            >
              <span className="flex flex-col">
                <span className="font-semibold">{e.title || t.progress.status[e.generation_status]}</span>
                <span className="text-muted text-sm">
                  {subjectLabel(e.subject)} · {levelLabel(e.level)}
                </span>
              </span>
              {e.generation_status !== "ready" ? (
                <span className="bg-surface-2 text-muted shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold">
                  {t.progress.status[e.generation_status]}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
      {exercises.hasNextPage ? (
        <Button
          variant="secondary"
          onClick={() => exercises.fetchNextPage()}
          loading={exercises.isFetchingNextPage}
        >
          {t.progress.more}
        </Button>
      ) : null}
    </Section>
  );
});
