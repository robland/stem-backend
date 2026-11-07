import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSyncExternalStore } from "react";
import { getSessionStatus, setAccessToken, subscribeSession } from "./auth";
import { getApi, getAuthApi, logout, unwrap } from "./client";
import type { components } from "./generated/schema.gen";

export type Schemas = components["schemas"];
export type Level = Schemas["LevelEnum"];
export type SubjectCode = Schemas["SubjectCodeEnum"];
export type Me = Schemas["Me"];
export type Register = Schemas["Register"];
export type PatchedMe = Schemas["PatchedMe"];
export type Progress = Schemas["Progress"];

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
    mutationFn: (body: { phone: string; password: string }) =>
      // Le corps réel ne contient que phone/password ; access/refresh sont en lecture seule.
      unwrap(getAuthApi().POST("/api/auth/login/", { body: body as Schemas["TokenObtainPair"] })),
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

export function useProgress() {
  return useQuery({
    queryKey: queryKeys.progress,
    queryFn: () => unwrap(getApi().GET("/api/progress/")),
  });
}
