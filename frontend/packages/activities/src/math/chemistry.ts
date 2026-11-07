// Formules chimiques (backend README §5.1) : éléments, parenthèses/crochets avec indice, hydrates (`·`),
// indices Unicode, charge `^{2+}`, `^2+`, `²⁺` ou signe seul (`Na+`), électron `e-`.
// Sert au compteur d'atomes de l'équilibrage (et, plus tard, à la correction hors-ligne).

export type Composition = { atoms: Record<string, number>; charge: number };

const SUBSCRIPTS: Record<string, string> = {
  "₀": "0",
  "₁": "1",
  "₂": "2",
  "₃": "3",
  "₄": "4",
  "₅": "5",
  "₆": "6",
  "₇": "7",
  "₈": "8",
  "₉": "9",
};
const SUPERSCRIPTS: Record<string, string> = {
  "⁰": "0",
  "¹": "1",
  "²": "2",
  "³": "3",
  "⁴": "4",
  "⁵": "5",
  "⁶": "6",
  "⁷": "7",
  "⁸": "8",
  "⁹": "9",
  "⁺": "+",
  "⁻": "-",
};

// Symboles du tableau périodique (1 → 118).
const ELEMENTS = new Set(
  (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr " +
    "Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir " +
    "Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl " +
    "Mc Lv Ts Og"
  ).split(" "),
);

/** Sépare la formule et sa charge ; renvoie null si la charge est mal écrite. */
function splitCharge(text: string): { body: string; charge: number } | null {
  const superscript = /([⁰-⁹¹²³]*)([⁺⁻])$/.exec(text);
  if (superscript) {
    const digits = [...superscript[1]!].map((c) => SUPERSCRIPTS[c]).join("");
    const sign = superscript[2] === "⁺" ? 1 : -1;
    return { body: text.slice(0, superscript.index), charge: sign * (digits ? Number(digits) : 1) };
  }
  const caret = /\^\{?(\d*)([+-])\}?$/.exec(text) ?? /\^\{?([+-])(\d*)\}?$/.exec(text);
  if (caret) {
    const [digits, sign] =
      /\d/.test(caret[1]!) || caret[1] === "" ? [caret[1]!, caret[2]!] : [caret[2]!, caret[1]!];
    return {
      body: text.slice(0, caret.index),
      charge: (sign === "+" ? 1 : -1) * (digits ? Number(digits) : 1),
    };
  }
  if (text.includes("^")) return null;
  const bare = /([+-]+)$/.exec(text); // Na+, SO4--, Cl-
  if (bare)
    return {
      body: text.slice(0, bare.index),
      charge: [...bare[1]!].reduce((c, s) => c + (s === "+" ? 1 : -1), 0),
    };
  return { body: text, charge: 0 };
}

function parseGroup(
  text: string,
  start: number,
  closing: string | null,
): { atoms: Record<string, number>; end: number } | null {
  const atoms: Record<string, number> = {};
  const add = (from: Record<string, number>, times: number) => {
    for (const [el, n] of Object.entries(from)) atoms[el] = (atoms[el] ?? 0) + n * times;
  };
  const count = (at: number) => {
    const digits = /^\d+/.exec(text.slice(at));
    return digits ? { n: Number(digits[0]), end: at + digits[0].length } : { n: 1, end: at };
  };
  let i = start;
  while (i < text.length) {
    const c = text[i]!;
    if (c === closing) return { atoms, end: i + 1 };
    if (c === "(" || c === "[") {
      const inner = parseGroup(text, i + 1, c === "(" ? ")" : "]");
      if (!inner) return null;
      const { n, end } = count(inner.end);
      add(inner.atoms, n);
      i = end;
    } else if (/[A-Z]/.test(c)) {
      const two = text.slice(i, i + 2);
      const symbol = /^[A-Z][a-z]$/.test(two) && ELEMENTS.has(two) ? two : c;
      if (!ELEMENTS.has(symbol)) return null;
      const { n, end } = count(i + symbol.length);
      add({ [symbol]: 1 }, n);
      i = end;
    } else {
      return null;
    }
  }
  return closing ? null : { atoms, end: i };
}

/** Composition d'une espèce (atomes et charge) ; null si la formule est illisible. */
export function parseFormula(input: string): Composition | null {
  const text = [...input.trim()]
    .map((c) => SUBSCRIPTS[c] ?? c)
    .join("")
    .replace(/\s+/g, "");
  if (!text) return null;
  if (text === "e-" || text === "e^-" || text === "e^{-}" || text === "e⁻") return { atoms: {}, charge: -1 };
  const split = splitCharge(text);
  if (!split || !split.body) return null;

  const atoms: Record<string, number> = {};
  // Hydrates : CuSO4·5H2O (aussi `.` ou `*`).
  for (const part of split.body.split(/[·.*]/)) {
    const multiplier = /^\d+/.exec(part);
    const group = parseGroup(part, multiplier ? multiplier[0].length : 0, null);
    if (!group || !Object.keys(group.atoms).length) return null;
    for (const [el, n] of Object.entries(group.atoms))
      atoms[el] = (atoms[el] ?? 0) + n * (multiplier ? Number(multiplier[0]) : 1);
  }
  return { atoms, charge: split.charge };
}

export type BalanceCheck = {
  elements: { element: string; left: number; right: number }[];
  charge: { left: number; right: number };
  balanced: boolean;
};

/** Bilan des atomes et des charges pour des coefficients donnés ; null si une espèce est illisible. */
export function checkBalance(
  reactants: string[],
  products: string[],
  coefficients: number[],
): BalanceCheck | null {
  const side = (species: string[], offset: number) => {
    const atoms: Record<string, number> = {};
    let charge = 0;
    for (const [i, formula] of species.entries()) {
      const composition = parseFormula(formula);
      if (!composition) return null;
      const k = coefficients[offset + i] ?? 1;
      for (const [el, n] of Object.entries(composition.atoms)) atoms[el] = (atoms[el] ?? 0) + n * k;
      charge += composition.charge * k;
    }
    return { atoms, charge };
  };
  const left = side(reactants, 0);
  const right = side(products, reactants.length);
  if (!left || !right) return null;
  const names = [...new Set([...Object.keys(left.atoms), ...Object.keys(right.atoms)])];
  const elements = names.map((element) => ({
    element,
    left: left.atoms[element] ?? 0,
    right: right.atoms[element] ?? 0,
  }));
  const balanced = elements.every((e) => e.left === e.right) && left.charge === right.charge;
  return { elements, charge: { left: left.charge, right: right.charge }, balanced };
}
