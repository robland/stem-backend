// Scanner : upload → extraction suivie en direct → correction / validation des énoncés → génération.
import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getApi, unwrap } from "./client";
import { EventsUnavailable, followEvents } from "./events";
import type { components } from "./generated/schema.gen";

type Schemas = components["schemas"];
export type Upload = Schemas["Upload"];
export type UploadStatus = Schemas["UploadStatusEnum"];
export type ExtractedExercise = Schemas["ExtractedExercise"];
export type ExtractedExercisePatch = Schemas["PatchedExtractedExercise"];
export type Exercise = Schemas["Exercise"];
export type GenerationStatus = Schemas["GenerationStatusEnum"];
/** `content` vaut null tant que le parcours n'est pas prêt (l'OpenAPI l'omet). */
export type ExerciseDetail = Omit<Schemas["ExerciseDetail"], "content"> & { content: unknown };

export const UPLOAD_TERMINAL: readonly UploadStatus[] = ["extracted", "error"];
export const GENERATION_TERMINAL: readonly GenerationStatus[] = ["ready", "needs_review", "error"];

/** Repli si le flux SSE est indisponible (README frontend §6). */
const POLL_MS = 3000;

export const ingestionKeys = {
  upload: (id: string) => ["uploads", id] as const,
  exercise: (id: string) => ["exercises", id] as const,
};

type LiveOptions<T> = {
  queryKey: QueryKey;
  queryFn: () => Promise<T>;
  eventsPath: string;
  status: (data: T) => string;
  terminal: readonly string[];
  enabled?: boolean;
};

/** Ressource à statut suivie en direct : SSE tant qu'elle n'est pas finale, polling si SSE impossible. */
function useLiveResource<T>({
  queryKey,
  queryFn,
  eventsPath,
  status,
  terminal,
  enabled = true,
}: LiveOptions<T>) {
  const queryClient = useQueryClient();
  const [polling, setPolling] = useState(false);
  const query = useQuery({
    queryKey,
    queryFn,
    enabled,
    refetchInterval: (q) =>
      polling && q.state.data && !terminal.includes(status(q.state.data)) ? POLL_MS : false,
  });
  const data = query.data;
  const loaded = data !== undefined;
  const isFinal = data !== undefined && terminal.includes(status(data));
  const key = JSON.stringify(queryKey);

  useEffect(() => {
    // Après le premier GET seulement : sinon sa réponse, plus ancienne, écraserait un événement déjà reçu.
    if (!enabled || !loaded || isFinal || polling) return;
    const controller = new AbortController();
    followEvents<T>(eventsPath, {
      terminal,
      signal: controller.signal,
      onUpdate: (_status, data) => {
        void queryClient.cancelQueries({ queryKey });
        queryClient.setQueryData(queryKey, data);
      },
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      if (error instanceof EventsUnavailable && error.reason === "gone") {
        void queryClient.invalidateQueries({ queryKey });
        return;
      }
      setPolling(true);
    });
    return () => controller.abort();
    // queryKey est suivi par sa forme sérialisée.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, eventsPath, enabled, loaded, isFinal, polling, queryClient]);

  return query;
}

export function useUpload(id: string | undefined) {
  return useLiveResource<Upload>({
    queryKey: ingestionKeys.upload(id ?? ""),
    queryFn: () => unwrap(getApi().GET("/api/uploads/{id}/", { params: { path: { id: id! } } })),
    eventsPath: `/api/uploads/${id}/events/`,
    status: (upload) => upload.status,
    terminal: UPLOAD_TERMINAL,
    enabled: Boolean(id),
  });
}

export function useExerciseLive(id: string | undefined) {
  return useLiveResource<ExerciseDetail>({
    queryKey: ingestionKeys.exercise(id ?? ""),
    queryFn: () => unwrap(getApi().GET("/api/exercises/{id}/", { params: { path: { id: id! } } })),
    eventsPath: `/api/exercises/${id}/events/`,
    status: (exercise) => exercise.generation_status,
    terminal: GENERATION_TERMINAL,
    enabled: Boolean(id),
  });
}

export function useCreateUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: Blob) => {
      const form = new FormData();
      form.append("file", file, file instanceof File ? file.name : "photo.jpg");
      // L'OpenAPI type `file` en chaîne : le corps réel est un FormData.
      return unwrap(
        getApi().POST("/api/uploads/", {
          body: form as never,
          bodySerializer: (body) => body as unknown as FormData,
        }),
      );
    },
    onSuccess: (upload) => queryClient.setQueryData(ingestionKeys.upload(upload.id), upload),
  });
}

function replaceExercise(
  queryClient: ReturnType<typeof useQueryClient>,
  uploadId: string,
  exercise: ExtractedExercise | null,
  id: string,
) {
  queryClient.setQueryData<Upload>(
    ingestionKeys.upload(uploadId),
    (upload) =>
      upload && {
        ...upload,
        exercises: exercise
          ? upload.exercises.map((e) => (e.id === id ? exercise : e))
          : upload.exercises.filter((e) => e.id !== id),
      },
  );
}

export function useUpdateExtracted(uploadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: ExtractedExercisePatch }) =>
      unwrap(getApi().PATCH("/api/extracted-exercises/{id}/", { params: { path: { id } }, body: patch })),
    onSuccess: (exercise) => replaceExercise(queryClient, uploadId, exercise, exercise.id),
  });
}

export function useDiscardExtracted(uploadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(getApi().DELETE("/api/extracted-exercises/{id}/", { params: { path: { id } } })).then(() => id),
    onSuccess: (id) => replaceExercise(queryClient, uploadId, null, id),
  });
}

export function useValidateExtracted(uploadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(getApi().POST("/api/extracted-exercises/{id}/validate/", { params: { path: { id } } })),
    onSuccess: (exercise) => replaceExercise(queryClient, uploadId, exercise, exercise.id),
  });
}

/** Lance la génération (202) ou renvoie le parcours existant / repris du cache (200). */
export function useGenerate() {
  return useMutation({
    mutationFn: (extractedId: string) =>
      unwrap(
        getApi().POST("/api/extracted-exercises/{id}/generate/", { params: { path: { id: extractedId } } }),
      ),
  });
}
