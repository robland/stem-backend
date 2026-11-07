import { isApiError } from "@stem/api-client";
import { errorMessage } from "./errors";
import { t } from "@/strings/fr";

const hour = new Intl.DateTimeFormat("fr-FR", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Africa/Brazzaville",
});

/** Message d'erreur d'envoi ou de génération, avec l'heure de `Retry-After` quand le quota est atteint. */
export function quotaAwareMessage(error: unknown): string {
  if (isApiError(error) && error.status === 429) {
    const at = error.retryAfter ? hour.format(error.retryAfter).replace(":", "h") : null;
    return t.scan.quota(error.detail ?? t.common.unknownError, at);
  }
  return errorMessage(error);
}
