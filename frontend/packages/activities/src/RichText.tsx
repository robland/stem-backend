import { cn } from "@stem/ui";
import { createElement, useEffect, useMemo, useRef, useState } from "react";
import { KATEX_OPTIONS, loadKatex, type Katex } from "./katex";
import { parseRichText } from "./richText";

function MathSegment({ tex, display }: { tex: string; display: boolean }) {
  const ref = useRef<HTMLElement>(null);
  const [katex, setKatex] = useState<Katex | null>(null);

  useEffect(() => {
    let alive = true;
    loadKatex()
      .then((k) => alive && setKatex(() => k))
      .catch(() => undefined); // hors ligne sans le module : la source LaTeX reste lisible
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    // katex.render écrit dans l'élément un balisage qu'il produit lui-même (entrée échappée, trust: false).
    if (katex && ref.current) katex.render(tex, ref.current, { ...KATEX_OPTIONS, displayMode: display });
  }, [katex, tex, display]);

  return createElement(
    display ? "div" : "span",
    { ref, className: cn(display && "my-2 overflow-x-auto", !katex && "font-mono text-[0.95em]") },
    katex ? null : tex,
  );
}

/** Affiche un texte riche : retours à la ligne conservés, formules par KaTeX. */
export function RichText({ text, className }: { text: string; className?: string }) {
  const segments = useMemo(() => parseRichText(text), [text]);
  return (
    <span className={cn("whitespace-pre-line", className)}>
      {segments.map((segment, i) =>
        segment.kind === "text" ? (
          <span key={i}>{segment.value}</span>
        ) : (
          <MathSegment key={i} tex={segment.value} display={segment.display} />
        ),
      )}
    </span>
  );
}
