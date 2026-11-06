"""Formules chimiques : lecture, composition atomique, conservation des atomes et des charges."""

import math
import re
from collections import Counter
from functools import reduce

ELEMENTS = set(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
    "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm "
    "Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No "
    "Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)
SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
# Charge finale : « ^{2+} », « ^2+ », « ^+ », « SO₄²⁻ », ou un signe seul (« Na+ »).
# Sans « ^ », un nombre avant le signe est un indice : « SO42- » serait ambigu.
CHARGE_RE = re.compile(r"\^\{?(\d*)([+-])\}?$|([+-])$")
SUPERSCRIPT_CHARGE_RE = re.compile(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]*[⁺⁻])$")
TOKEN_RE = re.compile(r"([A-Z][a-z]?)|(\d+)|([(\[])|([)\]])")


class FormulaError(ValueError):
    """Formule illisible ; le message s'adresse à l'élève."""


def normalize_formula(text):
    """Forme canonique d'une saisie : sans espaces, indices et exposants Unicode convertis."""
    text = re.sub(r"\s+", "", text or "").replace("−", "-").replace("•", "·").replace("*", "·")
    text = SUPERSCRIPT_CHARGE_RE.sub(lambda m: "^" + m.group(1).translate(SUPERSCRIPTS), text)
    return text.translate(SUBSCRIPTS)


def parse_formula(text):
    """« Ca(OH)2 », « CuSO4·5H2O », « SO4^{2-} » → (Counter des atomes, charge)."""
    formula = normalize_formula(text)
    if not formula or len(formula) > 100:
        raise FormulaError("Formule vide ou trop longue.")

    charge = 0
    match = CHARGE_RE.search(formula)
    if match:
        digits, sign = (match.group(1), match.group(2)) if match.group(2) else ("", match.group(3))
        charge = int(digits or 1) * (1 if sign == "+" else -1)
        formula = formula[: match.start()]
    if formula == "e":
        # Électron des demi-équations d'oxydoréduction : « e- », « e^- ».
        return Counter(), -1

    atoms = Counter()
    for part in formula.split("·"):
        coefficient_match = re.match(r"(\d*)(.*)", part)
        coefficient = int(coefficient_match.group(1) or 1)
        for element, count in _parse_group(coefficient_match.group(2)).items():
            atoms[element] += count * coefficient
    if not atoms:
        raise FormulaError(f"Formule illisible : {text}.")
    return atoms, charge


def _parse_group(formula):
    position = 0
    stack = [Counter()]
    last = None  # dernier élément ou groupe, auquel s'applique un indice
    while position < len(formula):
        match = TOKEN_RE.match(formula, position)
        if not match:
            raise FormulaError(f"Formule illisible : {formula}.")
        element, digits, opening, closing = match.groups()
        position = match.end()
        if element:
            if element not in ELEMENTS:
                raise FormulaError(f"Élément inconnu : {element}.")
            stack[-1][element] += 1
            last = Counter({element: 1})
        elif digits:
            if last is None or int(digits) == 0:
                raise FormulaError(f"Indice mal placé dans {formula}.")
            for name, count in last.items():
                stack[-1][name] += count * (int(digits) - 1)
            last = None
        elif opening:
            stack.append(Counter())
            last = None
        else:
            if len(stack) == 1:
                raise FormulaError(f"Parenthèses déséquilibrées dans {formula}.")
            group = stack.pop()
            stack[-1].update(group)
            last = group
    if len(stack) != 1:
        raise FormulaError(f"Parenthèses déséquilibrées dans {formula}.")
    return stack[0]


def balance_report(reactants, products, coefficients):
    """Écarts de conservation : liste de messages (vide si l'équation est équilibrée)."""
    if len(coefficients) != len(reactants) + len(products):
        return ["Il faut un coefficient par espèce."]
    if any(c < 1 for c in coefficients):
        return ["Les coefficients sont des entiers supérieurs ou égaux à 1."]

    left, right = Counter(), Counter()
    left_charge = right_charge = 0
    for formula, coefficient in zip(reactants, coefficients[: len(reactants)]):
        atoms, charge = parse_formula(formula)
        left.update({element: count * coefficient for element, count in atoms.items()})
        left_charge += charge * coefficient
    for formula, coefficient in zip(products, coefficients[len(reactants):]):
        atoms, charge = parse_formula(formula)
        right.update({element: count * coefficient for element, count in atoms.items()})
        right_charge += charge * coefficient

    issues = [
        f"Le nombre d'atomes de {element} n'est pas conservé ({left[element]} à gauche, {right[element]} à droite)."
        for element in sorted(left.keys() | right.keys())
        if left[element] != right[element]
    ]
    if left_charge != right_charge:
        issues.append(f"Les charges ne sont pas conservées ({left_charge:+d} à gauche, {right_charge:+d} à droite).")
    return issues


def is_simplest(coefficients):
    return reduce(math.gcd, coefficients) == 1
