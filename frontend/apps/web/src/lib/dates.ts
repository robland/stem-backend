// Dates affichées à l'élève, au fuseau de l'API (Africa/Brazzaville, backend README §5.3).
const TIME_ZONE = "Africa/Brazzaville";

const dayKey = new Intl.DateTimeFormat("en-CA", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const shortDate = new Intl.DateTimeFormat("fr-FR", { timeZone: TIME_ZONE, day: "numeric", month: "short" });

/** Nombre de jours calendaires (à Brazzaville) entre `now` et `date` ; négatif si passé. */
export function daysUntil(date: Date, now = new Date()) {
  const day = (d: Date) => Date.parse(`${dayKey.format(d)}T00:00:00Z`);
  return Math.round((day(date) - day(now)) / 86_400_000);
}

/** « aujourd'hui », « demain », « dans 3 jours », « le 12 nov. ». */
export function relativeDay(iso: string, now = new Date()) {
  const date = new Date(iso);
  const days = daysUntil(date, now);
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return "demain";
  if (days < 7) return `dans ${days} jours`;
  return `le ${shortDate.format(date)}`;
}
