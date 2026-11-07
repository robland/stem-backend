import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { getSessionStatus, setAccessToken, subscribeSession } from "./auth";
import { getApi, getAuthApi, logout, unwrap } from "./client";
import type { components } from "./generated/schema.gen";

export type Schemas = components["schemas"];
export type Level = Schemas["LevelEnum"];
export type Serie = Schemas["SerieEnum"];
export type SubjectCode = Schemas["SubjectCodeEnum"];
export type Me = Schemas["Me"];
export type Register = Schemas["Register"];
export type PatchedMe = Schemas["PatchedMe"];
export type Progress = Schemas["Progress"];
export type Mastery = Schemas["Mastery"];
export type ReviewItem = Schemas["ReviewItem"];
export type MasteryState = Schemas["StateEnum"];

export const queryKeys = {
  me: ["me"] as const,
  subjects: ["curriculum", "subjects"] as const,
  chapters: (subject?: SubjectCode, level?: Level) => ["curriculum", "chapters", subject, level] as const,
  progress: ["progress"] as const,
  exercises: ["exercises"] as const,
};

export function useSession() {
  return useSyncExternalStore(subscribeSession, getSessionStatus, getSessionStatus);
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["Login"]) => unwrap(getAuthApi().POST("/api/auth/login/", { body })),
    onSuccess: (data) => {
      queryClient.clear();
      setAccessToken(data.access);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (body: Register) => unwrap(getAuthApi().POST("/api/auth/register/", { body })),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => queryClient.clear(),
  });
}

export function useMe(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => unwrap(getApi().GET("/api/me/")),
    staleTime: 5 * 60_000,
    ...options,
  });
}

export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PatchedMe) => unwrap(getApi().PATCH("/api/me/", { body })),
    onSuccess: (me) => queryClient.setQueryData(queryKeys.me, me),
  });
}

/** Référentiel figé : mis en cache longtemps (data mobile chère). */
export function useSubjects() {
  return useQuery({
    queryKey: queryKeys.subjects,
    queryFn: () => unwrap(getApi().GET("/api/curriculum/subjects/")),
    staleTime: 24 * 60 * 60_000,
  });
}

export function useChapters(subject?: SubjectCode, level?: Level) {
  return useQuery({
    queryKey: queryKeys.chapters(subject, level),
    queryFn: () =>
      unwrap(getApi().GET("/api/curriculum/chapters/", { params: { query: { subject, level } } })),
    enabled: Boolean(subject),
    staleTime: 24 * 60 * 60_000,
  });
}

/** Curseur de la page suivante, lu dans l'URL `next` de DRF. */
export const cursorOf = (next: string | null | undefined) =>
  next ? (new URL(next, "http://x").searchParams.get("cursor") ?? undefined) : undefined;

/** Mes parcours, du plus récent au plus ancien, 20 par page ; éventuellement ceux d'un chapitre. */
export function useExercises(chapter?: string) {
  return useInfiniteQuery({
    queryKey: [...queryKeys.exercises, chapter ?? null],
    queryFn: ({ pageParam }) =>
      unwrap(getApi().GET("/api/exercises/", { params: { query: { cursor: pageParam, chapter } } })),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => cursorOf(page.next),
  });
}

export function useProgress() {
  return useQuery({
    queryKey: queryKeys.progress,
    queryFn: () => unwrap(getApi().GET("/api/progress/")),
  });
}
