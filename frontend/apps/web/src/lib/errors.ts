import { isApiError, isNetworkError } from "@stem/api-client";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { t } from "@/strings/fr";

/** Message lisible par l'élève pour une erreur de requête. */
export function errorMessage(error: unknown): string {
  if (isNetworkError(error)) return t.common.networkError;
  if (isApiError(error)) return error.detail ?? Object.values(error.fieldErrors)[0] ?? t.common.unknownError;
  return t.common.unknownError;
}

/** Reporte les erreurs DRF par champ sur le formulaire ; renvoie true si au moins une a été placée. */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: Path<T>[],
) {
  if (!isApiError(error)) return false;
  let placed = false;
  for (const [field, message] of Object.entries(error.fieldErrors)) {
    if ((fields as string[]).includes(field)) {
      setError(field as Path<T>, { message });
      placed = true;
    }
  }
  return placed;
}
