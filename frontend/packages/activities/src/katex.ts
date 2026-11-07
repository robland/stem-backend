// Déclarations ambiantes (CSS, mhchem) visibles aussi des apps qui compilent ce paquet depuis ses sources.
// eslint-disable-next-line @typescript-eslint/triple-slash-reference
/// <reference path="./modules.d.ts" />

export type Katex = typeof import("katex").default;

let katexPromise: Promise<Katex> | null = null;

/** KaTeX (+ mhchem et sa feuille de style) chargé à la première formule, jamais dans le bundle initial. */
export function loadKatex(): Promise<Katex> {
  katexPromise ??= Promise.all([import("katex"), import("katex/dist/katex.min.css")]).then(
    async ([module]) => {
      await import("katex/contrib/mhchem");
      return module.default;
    },
  );
  return katexPromise;
}

export const KATEX_OPTIONS = {
  throwOnError: false,
  trust: false, // aucune commande \href, \includegraphics…
  strict: "ignore" as const,
  maxSize: 20,
  maxExpand: 200,
  // Zone de saisie du contrat `formula_input` (MathLive) : affichée comme une case vide.
  macros: { "\\placeholder": "\\boxed{\\phantom{x}}" },
};
