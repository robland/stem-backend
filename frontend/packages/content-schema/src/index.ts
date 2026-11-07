import type { z } from "zod";
import {
  ACTIVITY_TYPES,
  ActivityPublic,
  ExerciseContent,
  ExerciseContentPublic,
  SCHEMA_VERSION,
  type ActivityType,
} from "./generated/content.gen";

export * from "./generated/content.gen";

export type ParseResult<T> = { ok: true; data: T } | { ok: false; error: z.ZodError };

/** Étape dont l'activité n'a pas pu être lue : affichée comme un état d'erreur, jamais un crash (README §4). */
export type InvalidStep = { id: string; reason: "unknown_type" | "invalid"; type?: string };

export const isKnownActivityType = (type: unknown): type is ActivityType =>
  typeof type === "string" && (ACTIVITY_TYPES as readonly string[]).includes(type);

export function parseContent(data: unknown): ParseResult<ExerciseContent> {
  const result = ExerciseContent.safeParse(data);
  return result.success ? { ok: true, data: result.data } : { ok: false, error: result.error };
}

export function parsePublicContent(data: unknown): ParseResult<ExerciseContentPublic> {
  const result = ExerciseContentPublic.safeParse(data);
  return result.success ? { ok: true, data: result.data } : { ok: false, error: result.error };
}

/**
 * Lit une activité publique isolément : une étape d'un type inconnu (schéma plus récent) ou mal formée
 * ne doit pas empêcher d'afficher les autres.
 */
export function parseActivity(data: unknown): { ok: true; data: ActivityPublic } | { ok: false; reason: InvalidStep["reason"] } {
  const type = (data as { type?: unknown } | null)?.type;
  if (!isKnownActivityType(type)) return { ok: false, reason: "unknown_type" };
  const result = ActivityPublic.safeParse(data);
  return result.success ? { ok: true, data: result.data } : { ok: false, reason: "invalid" };
}

export const isSupportedSchemaVersion = (version: unknown) => version === SCHEMA_VERSION;
