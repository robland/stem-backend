import { useMe, useProgress } from "@stem/api-client";
import { Button, Card, Spinner } from "@stem/ui";
import { Camera, Flame } from "lucide-react";
import { Link } from "react-router-dom";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

// Version minimale en attendant la maquette validée de l'accueil.
export function HomePage() {
  const me = useMe();
  const progress = useProgress();
  const review = progress.data?.review_today ?? [];

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold sm:text-3xl">{me.data ? t.home.hello(me.data.pseudo) : " "}</h1>
        {progress.data ? (
          <p className="flex items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1 text-sm font-semibold">
            <Flame aria-hidden className="size-4 text-accent" />
            {t.home.streak(progress.data.summary.streak_days)}
          </p>
        ) : null}
      </header>

      <Card className="flex flex-col gap-3 border-none bg-primary text-primary-fg sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-lg font-bold">{t.home.scanCta}</p>
          <p className="opacity-90">{t.home.scanCtaHint}</p>
        </div>
        <Button asChild variant="secondary" size="lg" className="border-none">
          <Link to={paths.scan}>
            <Camera aria-hidden className="size-5" />
            {t.nav.scan}
          </Link>
        </Button>
      </Card>

      <section aria-labelledby="review-title" className="flex flex-col gap-3">
        <h2 id="review-title" className="text-lg font-bold">
          {t.home.reviewToday}
        </h2>
        {progress.isPending ? <Spinner label={t.common.loading} /> : null}
        {progress.isSuccess && review.length === 0 ? <p className="text-muted">{t.home.reviewEmpty}</p> : null}
        <ul className="flex flex-col gap-2">
          {review.map((item) => (
            <li key={item.exercise.id}>
              <Card className="flex items-center justify-between gap-3">
                <span className="font-semibold">{item.exercise.title}</span>
                <span className="shrink-0 rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-muted">
                  {item.reason === "to_finish" ? t.home.toFinish : t.home.toReview}
                </span>
              </Card>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
