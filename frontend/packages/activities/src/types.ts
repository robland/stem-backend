import type { ActivityPublic, ActivityType } from "@stem/content-schema";
import { createContext, useContext, type ComponentType } from "react";

/** Détail de correction renvoyé par l'API (`details`, backend README §5.1) : par trou, paire, point… */
export type GradingDetails = Record<string, unknown> | null;

/**
 * Interface commune des renderers. La réponse est contrôlée par le lecteur : le bouton « Vérifier » vit dans
 * sa barre d'actions, et la réponse reste affichée (et corrigeable) après un essai faux.
 */
export type RendererProps<A, R> = {
  activity: A;
  value: R | undefined;
  onChange: (value: R) => void;
  disabled?: boolean;
  /** Réponse jugée : marque les éléments justes ou faux quand l'API les détaille. */
  details?: GradingDetails;
  /** Graine stable (identifiant de l'étape) pour mélanger sans changer d'un rendu à l'autre. */
  seed: string;
};

export type ActivityDefinition<A, R> = {
  Renderer: ComponentType<RendererProps<A, R>>;
  /** Valeur de départ (ordre mélangé, curseurs à leur position initiale…). */
  initial?: (activity: A, seed: string) => R;
  /** Réponse complète : active le bouton « Vérifier ». */
  isComplete: (activity: A, value: R | undefined) => boolean;
  /** La consigne est rendue par le renderer lui-même (ex. formule à compléter). */
  ownsPrompt?: boolean;
  /** Réponse envoyée à l'API (format backend README §5.1) ; par défaut la valeur telle quelle. */
  serialize?: (value: R) => unknown;
};

export type ActivityOf<T extends ActivityType> = Extract<ActivityPublic, { type: T }>;

export type FormulaInputMode = "simple" | "mathlive";

export type ActivitySettings = { formulaInput: FormulaInputMode };

export const ActivitySettingsContext = createContext<ActivitySettings>({ formulaInput: "simple" });
export const useActivitySettings = () => useContext(ActivitySettingsContext);
