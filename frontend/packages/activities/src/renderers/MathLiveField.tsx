// Variante d'évaluation de la saisie de formules : clavier mathématique MathLive (chargé à la demande).
// La valeur reste l'expression ASCII du contrat (backend README §5.1), lue par `getValue("ascii-math")`.
import { Alert } from "@stem/ui";
import { useEffect, useRef, useState } from "react";
import { loadKatex } from "../katex";
import { s } from "../strings";
import type { FieldProps } from "./formula";

type MathfieldLike = HTMLElement & {
  value: string;
  getValue(format: "ascii-math"): string;
  setValue(value: string, options?: { format?: "ascii-math" }): void;
  mathVirtualKeyboardPolicy: "auto" | "manual";
  smartFence: boolean;
  disabled: boolean;
};

/** ASCIIMath de MathLive → syntaxe du backend (`xx` = ×, `·` …). */
export function fromMathLive(ascii: string, latex: string) {
  let out = ascii.replace(/·|⋅/g, "*");
  if (latex.includes("\\times")) out = out.replace(/xx/g, "*");
  return out.trim();
}

let ready: Promise<void> | null = null;

function loadMathLive() {
  ready ??= Promise.all([loadKatex(), import("mathlive")]).then(([, { MathfieldElement }]) => {
    // Polices KaTeX déjà fournies par la feuille de KaTeX ; aucun son (data mobile).
    MathfieldElement.fontsDirectory = null;
    MathfieldElement.soundsDirectory = null;
  });
  return ready;
}

export default function MathLiveField({ value, onChange, disabled, describedBy }: FieldProps) {
  const host = useRef<HTMLDivElement>(null);
  const field = useRef<MathfieldLike | null>(null);
  const [failed, setFailed] = useState(false);
  const change = useRef(onChange);
  change.current = onChange;

  useEffect(() => {
    let alive = true;
    loadMathLive()
      .then(() => {
        if (!alive || !host.current) return;
        const mf = document.createElement("math-field") as MathfieldLike;
        mf.mathVirtualKeyboardPolicy = "auto";
        mf.smartFence = true;
        mf.setAttribute("aria-label", s.formula);
        if (describedBy) mf.setAttribute("aria-describedby", describedBy);
        mf.className = "block w-full rounded-lg border border-border bg-surface p-2 text-xl";
        if (value) mf.setValue(value, { format: "ascii-math" });
        mf.addEventListener("input", () => change.current(fromMathLive(mf.getValue("ascii-math"), mf.value)));
        host.current.replaceChildren(mf);
        field.current = mf;
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
    // Monté une seule fois ; la valeur initiale vient de la réponse déjà saisie.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (field.current) field.current.disabled = Boolean(disabled);
  }, [disabled]);

  if (failed) return <Alert tone="info">{s.formulaUnavailable}</Alert>;
  return <div ref={host} className="min-h-12" />;
}
