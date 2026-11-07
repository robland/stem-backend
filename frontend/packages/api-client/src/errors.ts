/** Erreur HTTP de l'API. `data` contient le corps DRF (erreurs par champ, `detail`…). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly data: unknown,
    readonly retryAfter: Date | null = null,
  ) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
  }

  /** Message global (`detail` / `non_field_errors`, ou liste de messages DRF), sinon null. */
  get detail(): string | null {
    if (Array.isArray(this.data)) return typeof this.data[0] === "string" ? this.data[0] : null;
    const data = this.data as Record<string, unknown> | null;
    const value = data?.detail ?? data?.non_field_errors;
    if (typeof value === "string") return value;
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    return null;
  }

  /** Erreurs par champ, premier message de chacun. */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    const data = this.data;
    if (!data || typeof data !== "object" || Array.isArray(data)) return out;
    for (const [key, value] of Object.entries(data)) {
      if (key === "detail" || key === "non_field_errors") continue;
      const message = Array.isArray(value) ? value[0] : value;
      if (typeof message === "string") out[key] = message;
    }
    return out;
  }
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;

/** `Retry-After` en secondes ou en date HTTP. */
export function parseRetryAfter(value: string | null, now = Date.now()): Date | null {
  if (!value) return null;
  const seconds = Number(value);
  if (Number.isFinite(seconds)) return new Date(now + seconds * 1000);
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export const isNetworkError = (error: unknown) => error instanceof TypeError;
