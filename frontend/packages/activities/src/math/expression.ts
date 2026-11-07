// Expressions ASCII du contrat (backend README §5.1) : nombres, variables d'une lettre, + - * / ^ (ou **),
// parenthèses, multiplication implicite (2x, 2(x+1), xy, (x+1)(x-1)), fonctions sqrt sin cos tan exp ln log
// abs, constantes pi et e. Sert à l'aperçu de la saisie, au tracé des courbes et, plus tard, à la correction
// hors-ligne. Comme SymPy côté serveur, `log` est le logarithme népérien.

export const MAX_EXPRESSION_LENGTH = 200;
export const FUNCTIONS = ["sqrt", "sin", "cos", "tan", "exp", "ln", "log", "abs"] as const;
export const CONSTANTS = ["pi", "e"] as const;
export type FunctionName = (typeof FUNCTIONS)[number];

export type Node =
  | { kind: "num"; value: number; text: string }
  | { kind: "var"; name: string }
  | { kind: "const"; name: "pi" | "e" }
  | { kind: "neg"; arg: Node }
  | { kind: "bin"; op: "+" | "-" | "*" | "/" | "^"; left: Node; right: Node; implicit?: boolean }
  | { kind: "call"; fn: FunctionName; arg: Node };

export class ExpressionError extends Error {
  constructor(
    readonly code: "empty" | "too_long" | "unexpected" | "unclosed" | "unknown_function" | "missing_operand",
    readonly position: number,
  ) {
    super(code);
    this.name = "ExpressionError";
  }
}

type Token =
  | { t: "num"; value: number; text: string; pos: number }
  | { t: "id"; name: string; pos: number }
  | { t: "fn"; name: FunctionName; pos: number }
  | { t: "op"; op: "+" | "-" | "*" | "/" | "^"; pos: number }
  | { t: "("; pos: number }
  | { t: ")"; pos: number };

/** Écritures Unicode courantes (clavier de téléphone, copier-coller) → ASCII. */
export function normalizeExpression(input: string): string {
  return input
    .replace(/[−–]/g, "-")
    .replace(/[×·⋅]/g, "*")
    .replace(/÷/g, "/")
    .replace(/²/g, "^2")
    .replace(/³/g, "^3")
    .replace(/√/g, "sqrt")
    .replace(/π/g, "pi")
    .replace(/\*\*/g, "^")
    .replace(/(\d),(\d)/g, "$1.$2");
}

const NAMES = [...FUNCTIONS, ...CONSTANTS].sort((a, b) => b.length - a.length);

function tokenize(source: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < source.length) {
    const c = source[i]!;
    if (c === " ") {
      i++;
    } else if (/[0-9.]/.test(c)) {
      const match = /^(\d+\.?\d*|\.\d+)/.exec(source.slice(i));
      if (!match) throw new ExpressionError("unexpected", i);
      tokens.push({ t: "num", value: Number(match[0]), text: match[0], pos: i });
      i += match[0].length;
    } else if (/[a-zA-Z]/.test(c)) {
      // Lettres collées : noms connus d'abord (sin, pi…), sinon une variable par lettre (xy = x·y).
      const name = NAMES.find((n) => source.startsWith(n, i));
      if (name && (FUNCTIONS as readonly string[]).includes(name)) {
        tokens.push({ t: "fn", name: name as FunctionName, pos: i });
        i += name.length;
      } else if (name) {
        tokens.push({ t: "id", name, pos: i });
        i += name.length;
      } else {
        tokens.push({ t: "id", name: c, pos: i });
        i++;
      }
    } else if ("+-*/^".includes(c)) {
      tokens.push({ t: "op", op: c as "+", pos: i });
      i++;
    } else if (c === "(" || c === ")") {
      tokens.push({ t: c, pos: i });
      i++;
    } else {
      throw new ExpressionError("unexpected", i);
    }
  }
  return tokens;
}

/** Analyse une saisie ; lève `ExpressionError` avec la position fautive. */
export function parseExpression(input: string): Node {
  const source = normalizeExpression(input).trim();
  if (!source) throw new ExpressionError("empty", 0);
  if (source.length > MAX_EXPRESSION_LENGTH) throw new ExpressionError("too_long", MAX_EXPRESSION_LENGTH);
  const tokens = tokenize(source);
  let index = 0;
  const peek = () => tokens[index];
  const next = () => tokens[index++];
  const end = () => source.length;

  // Début possible d'un facteur juxtaposé (multiplication implicite).
  const startsFactor = (token: Token | undefined) =>
    token !== undefined && (token.t === "num" || token.t === "id" || token.t === "fn" || token.t === "(");

  function primary(): Node {
    const token = next();
    if (!token) throw new ExpressionError("missing_operand", end());
    switch (token.t) {
      case "num":
        return { kind: "num", value: token.value, text: token.text };
      case "id":
        return token.name === "pi" || token.name === "e"
          ? { kind: "const", name: token.name }
          : { kind: "var", name: token.name };
      case "fn": {
        const open = next();
        if (open?.t !== "(") throw new ExpressionError("unexpected", open?.pos ?? end());
        const arg = sum();
        const close = next();
        if (close?.t !== ")") throw new ExpressionError("unclosed", open.pos);
        return { kind: "call", fn: token.name, arg };
      }
      case "(": {
        const inner = sum();
        const close = next();
        if (close?.t !== ")") throw new ExpressionError("unclosed", token.pos);
        return inner;
      }
      default:
        throw new ExpressionError(token.t === ")" ? "unexpected" : "missing_operand", token.pos);
    }
  }

  function power(): Node {
    const base = primary();
    const token = peek();
    if (token?.t === "op" && token.op === "^") {
      next();
      return { kind: "bin", op: "^", left: base, right: unary() }; // associatif à droite : 2^3^2 = 2^(3^2)
    }
    return base;
  }

  function unary(): Node {
    const token = peek();
    if (token?.t === "op" && (token.op === "-" || token.op === "+")) {
      next();
      const arg = unary();
      return token.op === "-" ? { kind: "neg", arg } : arg;
    }
    return power();
  }

  function product(): Node {
    let left = unary();
    for (;;) {
      const token = peek();
      if (token?.t === "op" && (token.op === "*" || token.op === "/")) {
        next();
        left = { kind: "bin", op: token.op, left, right: unary() };
      } else if (startsFactor(token)) {
        left = { kind: "bin", op: "*", left, right: power(), implicit: true };
      } else {
        return left;
      }
    }
  }

  function sum(): Node {
    let left = product();
    for (;;) {
      const token = peek();
      if (token?.t === "op" && (token.op === "+" || token.op === "-")) {
        next();
        left = { kind: "bin", op: token.op, left, right: product() };
      } else {
        return left;
      }
    }
  }

  const tree = sum();
  const rest = peek();
  if (rest) throw new ExpressionError("unexpected", rest.pos);
  return tree;
}

const PRECEDENCE = { "+": 1, "-": 1, "*": 2, "/": 2, neg: 3, "^": 4 } as const;
const precedence = (node: Node) =>
  node.kind === "bin" ? PRECEDENCE[node.op] : node.kind === "neg" ? PRECEDENCE.neg : 5;

const LATEX_FUNCTIONS: Record<FunctionName, (arg: string) => string> = {
  sqrt: (a) => `\\sqrt{${a}}`,
  abs: (a) => `\\left|${a}\\right|`,
  exp: (a) => `\\mathrm{e}^{${a}}`,
  sin: (a) => `\\sin\\left(${a}\\right)`,
  cos: (a) => `\\cos\\left(${a}\\right)`,
  tan: (a) => `\\tan\\left(${a}\\right)`,
  ln: (a) => `\\ln\\left(${a}\\right)`,
  log: (a) => `\\log\\left(${a}\\right)`,
};

const paren = (latex: string) => `\\left(${latex}\\right)`;

/** Écriture LaTeX fidèle à la saisie (pour l'aperçu KaTeX). */
export function toLatex(node: Node): string {
  switch (node.kind) {
    case "num":
      return node.text.replace(".", "{,}");
    case "var":
      return node.name;
    case "const":
      return node.name === "pi" ? "\\pi" : "\\mathrm{e}";
    case "neg": {
      const arg = toLatex(node.arg);
      return `-${precedence(node.arg) <= PRECEDENCE["-"] ? paren(arg) : arg}`;
    }
    case "call":
      return LATEX_FUNCTIONS[node.fn](toLatex(node.arg));
    case "bin": {
      const { op, left, right } = node;
      if (op === "/") return `\\frac{${toLatex(left)}}{${toLatex(right)}}`;
      if (op === "^") {
        const base = toLatex(left);
        return `${precedence(left) < 5 || left.kind === "call" ? paren(base) : base}^{${toLatex(right)}}`;
      }
      const p = PRECEDENCE[op];
      const l = toLatex(left);
      let r = toLatex(right);
      const lp = precedence(left) < p ? paren(l) : l;
      // a - (b + c), a · (−b) : parenthèses nécessaires à droite.
      if (
        precedence(right) < p ||
        (op === "-" && precedence(right) === p) ||
        (op === "*" && right.kind === "neg")
      ) {
        r = paren(r);
      }
      if (op === "*") {
        const juxtapose =
          node.implicit && !(right.kind === "num" || (right.kind === "bin" && right.left.kind === "num"));
        return juxtapose ? `${lp}${r}` : `${lp} \\times ${r}`;
      }
      return `${lp} ${op} ${r}`;
    }
  }
}

const FUNCTION_VALUES: Record<FunctionName, (x: number) => number> = {
  sqrt: Math.sqrt,
  sin: Math.sin,
  cos: Math.cos,
  tan: Math.tan,
  exp: Math.exp,
  ln: Math.log,
  log: Math.log,
  abs: Math.abs,
};

/** Valeur numérique ; NaN si une variable manque ou hors domaine. */
export function evaluate(node: Node, vars: Record<string, number>): number {
  switch (node.kind) {
    case "num":
      return node.value;
    case "var":
      return vars[node.name] ?? NaN;
    case "const":
      return node.name === "pi" ? Math.PI : Math.E;
    case "neg":
      return -evaluate(node.arg, vars);
    case "call":
      return FUNCTION_VALUES[node.fn](evaluate(node.arg, vars));
    case "bin": {
      const a = evaluate(node.left, vars);
      const b = evaluate(node.right, vars);
      switch (node.op) {
        case "+":
          return a + b;
        case "-":
          return a - b;
        case "*":
          return a * b;
        case "/":
          return a / b;
        case "^":
          return a ** b;
      }
    }
  }
}

/** Variables utilisées (hors constantes). */
export function variables(node: Node, found = new Set<string>()): Set<string> {
  if (node.kind === "var") found.add(node.name);
  else if (node.kind === "neg" || node.kind === "call") variables(node.arg, found);
  else if (node.kind === "bin") {
    variables(node.left, found);
    variables(node.right, found);
  }
  return found;
}

/** Compile une fonction d'une variable (tracés) ; null si l'expression est illisible. */
export function compileFunction(
  source: string,
  params: Record<string, number> = {},
): ((x: number) => number) | null {
  try {
    const tree = parseExpression(source);
    return (x) => evaluate(tree, { ...params, x });
  } catch {
    return null;
  }
}
