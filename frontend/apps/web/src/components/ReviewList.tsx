import type { ReviewItem } from "@stem/api-client";
import { Link } from "react-router-dom";
import { relativeDay } from "@/lib/dates";
import { paths } from "@/paths";
import { t } from "@/strings/fr";

/** « Révision du jour » (accueil et Progrès) : un parcours « à terminer » rouvre sa tentative. */
export function ReviewList({ items }: { items: ReviewItem[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item) => (
        <li key={item.exercise.id}>
          <Link
            to={paths.exercise(item.exercise.id, { tentative: item.attempt ?? undefined })}
            className="min-h-touch border-border bg-surface hover:bg-surface-2 flex items-center justify-between gap-3 rounded-xl border p-4"
          >
            <span className="flex flex-col">
              <span className="font-semibold">{item.exercise.title}</span>
              <span className="text-muted text-sm">
                {item.last_score !== null
                  ? t.progress.lastScore(item.last_score)
                  : t.progress.due(relativeDay(item.due_at))}
              </span>
            </span>
            <span className="bg-surface-2 text-muted shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold">
              {item.reason === "to_finish" ? t.home.toFinish : t.home.toReview}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
