// Texte riche du contrat (backend README §6.1) : texte + `$…$` / `$$…$$` (KaTeX) + `\ce{…}` (mhchem).
// Jamais de HTML : le texte est rendu comme texte, les formules par KaTeX.

export type Segment = { kind: "text"; value: string } | { kind: "math"; value: string; display: boolean };

/** Accolades équilibrées à partir de `start` (qui pointe sur `{`) ; renvoie l'indice après `}` ou -1. */
function closingBrace(text: string, start: number): number {
  let depth = 0;
  for (let i = start; i < text.length; i++) {
    const c = text[i];
    if (c === "\\") {
      i++;
      continue;
    }
    if (c === "{") depth++;
    else if (c === "}" && --depth === 0) return i + 1;
  }
  return -1;
}

/** Fin d'une formule ouverte par `delimiter` à partir de `from`, en sautant les `\$` ; -1 si non fermée. */
function closingDollar(text: string, from: number, delimiter: "$" | "$$"): number {
  for (let i = from; i < text.length; i++) {
    if (text[i] === "\\") {
      i++;
      continue;
    }
    if (text.startsWith(delimiter, i)) return i;
  }
  return -1;
}

export function parseRichText(text: string): Segment[] {
  const segments: Segment[] = [];
  let buffer = "";
  const flush = () => {
    if (buffer) segments.push({ kind: "text", value: buffer });
    buffer = "";
  };

  let i = 0;
  while (i < text.length) {
    if (text.startsWith("\\$", i)) {
      buffer += "$";
      i += 2;
      continue;
    }
    if (text.startsWith("\\ce{", i)) {
      const end = closingBrace(text, i + 3);
      if (end !== -1) {
        flush();
        segments.push({ kind: "math", value: text.slice(i, end), display: false });
        i = end;
        continue;
      }
    }
    if (text[i] === "$") {
      const display = text.startsWith("$$", i);
      const delimiter = display ? "$$" : "$";
      const start = i + delimiter.length;
      const end = closingDollar(text, start, delimiter);
      if (end !== -1 && end > start) {
        flush();
        segments.push({ kind: "math", value: text.slice(start, end).trim(), display });
        i = end + delimiter.length;
        continue;
      }
    }
    buffer += text[i];
    i++;
  }
  flush();
  return segments;
}
