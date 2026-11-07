// Tentatives en ligne (backend README §5.2) : étapes dans l'ordre, indices comptés par le serveur,
// réponses idempotentes par `client_uuid`.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getApi, unwrap } from "./client";
import type { components } from "./generated/schema.gen";
import { queryKeys } from "./hooks";

type Schemas = components["schemas"];
export type Attempt = Schemas["Attempt"];
export type StepState = Schemas["StepState"];
export type AnswerResult = Schemas["AnswerResult"];
export type Hint = Schemas["Hint"];

export const attemptKeys = { attempt: (id: string) => ["attempts", id] as const };

export function useAttempt(id: string | null) {
  return useQuery({
    queryKey: attemptKeys.attempt(id ?? ""),
    queryFn: () => unwrap(getApi().GET("/api/attempts/{id}/", { params: { path: { id: id! } } })),
    enabled: Boolean(id),
    staleTime: Infinity, // tenu à jour par les réponses aux mutations
  });
}

/** Démarre une tentative ; l'`id` généré par le client rend l'appel idempotent (réseau instable). */
export function useStartAttempt(exerciseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        getApi().POST("/api/exercises/{id}/attempts/", {
          params: { path: { id: exerciseId } },
          body: { id },
        }),
      ),
    onSuccess: (attempt) => queryClient.setQueryData(attemptKeys.attempt(attempt.id), attempt),
  });
}

export type AnswerInput = { step_id: string; response: unknown; client_uuid: string };

export function useSubmitAnswer(attemptId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AnswerInput) =>
      unwrap(getApi().POST("/api/attempts/{id}/answers/", { params: { path: { id: attemptId } }, body })),
    // Le serveur renvoie la tentative à jour ; une tentative finie change la progression.
    onSuccess: (result) => {
      queryClient.setQueryData(attemptKeys.attempt(attemptId), result.attempt);
      if (result.attempt.finished_at) void queryClient.invalidateQueries({ queryKey: queryKeys.progress });
    },
  });
}

export function useHint(attemptId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) =>
      unwrap(
        getApi().POST("/api/attempts/{id}/hints/", {
          params: { path: { id: attemptId } },
          body: { step_id: stepId },
        }),
      ),
    onSuccess: (hint) =>
      queryClient.setQueryData<Attempt>(
        attemptKeys.attempt(attemptId),
        (attempt) =>
          attempt && {
            ...attempt,
            hints_used: attempt.hints_used + 1,
            steps: attempt.steps.map((s) =>
              s.step_id === hint.step_id
                ? { ...s, hints_used: hint.level, hints: [...s.hints, hint.hint] }
                : s,
            ),
          },
      ),
  });
}
