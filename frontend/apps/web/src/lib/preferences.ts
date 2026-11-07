// Préférences locales à l'appareil (aucune n'est envoyée à l'API) : apparence, police, et les choix
// d'onboarding que l'API ne stocke pas (matières, objectif) — décision du porteur du projet, 2026-11-07.
import type { SubjectCode } from "@stem/api-client";
import { useSyncExternalStore } from "react";
import type { Goal } from "@/strings/fr";

export type Theme = "system" | "light" | "dark";

export type Preferences = {
  theme: Theme;
  dyslexicFont: boolean;
  subjects: SubjectCode[];
  goal: Goal | null;
};

const KEY = "stem.preferences";
const DEFAULTS: Preferences = { theme: "system", dyslexicFont: false, subjects: [], goal: null };

function read(): Preferences {
  try {
    return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<Preferences>) };
  } catch {
    return DEFAULTS;
  }
}

let current = read();
const listeners = new Set<() => void>();

export function getPreferences() {
  return current;
}

export function setPreferences(patch: Partial<Preferences>) {
  current = { ...current, ...patch };
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    /* stockage indisponible (navigation privée) : préférences gardées pour la session */
  }
  applyPreferences(current);
  listeners.forEach((listener) => listener());
}

export function usePreferences() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getPreferences,
    getPreferences,
  );
}

const darkQuery = () => window.matchMedia?.("(prefers-color-scheme: dark)");

export function applyPreferences(prefs: Preferences = current) {
  const root = document.documentElement;
  const dark = prefs.theme === "dark" || (prefs.theme === "system" && Boolean(darkQuery()?.matches));
  root.dataset.theme = dark ? "dark" : "light";
  if (prefs.dyslexicFont) {
    // Chargée à la demande : jamais dans le bundle initial.
    void import("@fontsource/opendyslexic/400.css");
    void import("@fontsource/opendyslexic/700.css");
    root.dataset.font = "dyslexic";
  } else {
    delete root.dataset.font;
  }
}

/** Suit le thème du système quand l'élève a choisi « Automatique ». */
export function watchSystemTheme() {
  const query = darkQuery();
  const onChange = () => current.theme === "system" && applyPreferences();
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}
