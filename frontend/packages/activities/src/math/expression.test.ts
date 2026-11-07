import {
  compileFunction,
  evaluate,
  ExpressionError,
  parseExpression,
  toLatex,
  variables,
} from "./expression";

const value = (source: string, vars: Record<string, number> = {}) => evaluate(parseExpression(source), vars);
const latex = (source: string) => toLatex(parseExpression(source));

describe("parseExpression", () => {
  it.each([
    ["2*x - 4", { x: 3 }, 2],
    ["2x-4", { x: 3 }, 2],
    ["2(x+1)", { x: 1 }, 4],
    ["(x+1)(x-1)", { x: 3 }, 8],
    ["xy", { x: 2, y: 5 }, 10],
    ["x^2 - 4*x + 3", { x: 1 }, 0],
    ["x**2", { x: 3 }, 9],
    ["-x^2", { x: 3 }, -9],
    ["2^3^2", {}, 512],
    ["3x/2", { x: 4 }, 6],
    ["sqrt(16) + abs(-2)", {}, 6],
    ["2pi", {}, 2 * Math.PI],
    ["ln(e)", {}, 1],
    ["x²−4x", { x: 5 }, 5],
    ["2,5x", { x: 2 }, 5],
    ["3 × 2 ÷ 4", {}, 1.5],
  ])("%s", (source, vars, expected) => {
    expect(value(source, vars)).toBeCloseTo(expected);
  });

  it("reconnaît les variables, pas les fonctions ni les constantes", () => {
    expect([...variables(parseExpression("a*sin(x) + pi*e*b"))].sort()).toEqual(["a", "b", "x"]);
  });

  it.each([
    ["", "empty"],
    ["2 +", "missing_operand"],
    ["(x + 1", "unclosed"],
    ["x + 1)", "unexpected"],
    ["sin x", "unexpected"],
    ["x # 2", "unexpected"],
    ["x".repeat(201), "too_long"],
  ])("refuse « %s » (%s)", (source, code) => {
    expect(() => parseExpression(source)).toThrow(ExpressionError);
    try {
      parseExpression(source);
    } catch (error) {
      expect((error as ExpressionError).code).toBe(code);
    }
  });
});

describe("toLatex", () => {
  it.each([
    ["2x - 4", "2x - 4"],
    ["2*3", "2 \\times 3"],
    ["(x+1)/2", "\\frac{x + 1}{2}"],
    ["2(x+1)", "2\\left(x + 1\\right)"],
    ["x - (y - 1)", "x - \\left(y - 1\\right)"],
    ["(x+1)^2", "\\left(x + 1\\right)^{2}"],
    ["-(x+1)", "-\\left(x + 1\\right)"],
    ["sqrt(x)", "\\sqrt{x}"],
    ["2.5x", "2{,}5x"],
    ["x(-2)", "x\\left(-2\\right)"],
    ["x*-2", "x \\times \\left(-2\\right)"],
  ])("%s → %s", (source, expected) => {
    expect(latex(source)).toBe(expected);
  });
});

describe("compileFunction", () => {
  it("compile une fonction paramétrée", () => {
    expect(compileFunction("a*x + b", { a: 2, b: -1 })?.(3)).toBe(5);
  });

  it("renvoie null pour une expression illisible", () => {
    expect(compileFunction("a*x +")).toBeNull();
  });
});
