import { checkBalance, parseFormula } from "./chemistry";

describe("parseFormula", () => {
  it.each([
    ["H2O", { H: 2, O: 1 }, 0],
    ["Ca(OH)2", { Ca: 1, O: 2, H: 2 }, 0],
    ["Al2(SO4)3", { Al: 2, S: 3, O: 12 }, 0],
    ["CuSO4·5H2O", { Cu: 1, S: 1, O: 9, H: 10 }, 0],
    ["H₂O", { H: 2, O: 1 }, 0],
    ["Fe^{3+}", { Fe: 1 }, 3],
    ["SO4^2-", { S: 1, O: 4 }, -2],
    ["SO₄²⁻", { S: 1, O: 4 }, -2],
    ["Na+", { Na: 1 }, 1],
    ["Cl-", { Cl: 1 }, -1],
    ["K4[Fe(CN)6]", { K: 4, Fe: 1, C: 6, N: 6 }, 0],
    ["Co", { Co: 1 }, 0],
    ["CO", { C: 1, O: 1 }, 0],
  ])("%s", (formula, atoms, charge) => {
    expect(parseFormula(formula)).toEqual({ atoms, charge });
  });

  it("reconnaît l'électron", () => {
    expect(parseFormula("e-")).toEqual({ atoms: {}, charge: -1 });
  });

  it.each(["", "Xy", "H2O)", "(OH", "h2o", "Fe^{3"])("refuse « %s »", (formula) => {
    expect(parseFormula(formula)).toBeNull();
  });
});

describe("checkBalance", () => {
  it("compte les atomes de chaque côté", () => {
    const check = checkBalance(["H2", "O2"], ["H2O"], [1, 1, 1]);
    expect(check?.balanced).toBe(false);
    expect(check?.elements).toEqual([
      { element: "H", left: 2, right: 2 },
      { element: "O", left: 2, right: 1 },
    ]);
  });

  it("valide une équation équilibrée", () => {
    expect(checkBalance(["H2", "O2"], ["H2O"], [2, 1, 2])?.balanced).toBe(true);
  });

  it("tient compte des charges et des électrons", () => {
    expect(checkBalance(["Fe^{3+}", "e-"], ["Fe^{2+}"], [1, 1, 1])?.balanced).toBe(true);
    expect(checkBalance(["Fe^{3+}"], ["Fe^{2+}"], [1, 1])?.balanced).toBe(false);
  });
});
