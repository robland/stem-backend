/** Texte riche → texte à lire par la synthèse vocale : sans délimiteurs ni commandes LaTeX. */
export function speakable(text: string) {
  return text
    .replace(/\\ce\{([^}]*)\}/g, "$1")
    .replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, "$1 sur $2")
    .replace(/\^\{?2\}?/g, " au carré")
    .replace(/\\placeholder(\{\})?/g, " … ")
    .replace(/\$|\\[a-zA-Z]+|[{}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
