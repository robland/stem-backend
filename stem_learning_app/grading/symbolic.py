"""Équivalence d'expressions mathématiques avec SymPy.

`parse_expr` s'appuie sur `eval` : la saisie est d'abord filtrée par liste blanche
(caractères, identifiants), évaluée sans builtins, et les exposants démesurés sont
refusés avant toute évaluation (« 9^9^9 »).
"""

import cmath
import random
import re
from tokenize import TokenError

from sympy import (
    Abs, Add, E, Float, Integer, Mul, Pow, Rational, Symbol, cos, exp, log, pi, sin, sqrt, tan,
)
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr, standard_transformations,
)

MAX_LENGTH = 200
MAX_EXPONENT = 100
SAMPLES = 12

ALLOWED_CHARS_RE = re.compile(r"^[0-9A-Za-z_+\-*/^().\s]*$")
IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FUNCTIONS = {"sqrt": sqrt, "sin": sin, "cos": cos, "tan": tan, "exp": exp, "ln": log, "log": log, "abs": Abs}
CONSTANTS = {"pi": pi, "e": E}
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
SAFE_GLOBALS = {
    "__builtins__": {},
    "Add": Add, "Mul": Mul, "Pow": Pow, "Symbol": Symbol,
    "Integer": Integer, "Float": Float, "Rational": Rational,
    **FUNCTIONS, **CONSTANTS,
}


class ExpressionError(ValueError):
    """Expression illisible ; le message s'adresse à l'élève."""


def parse(text, variables):
    """Texte ASCII (`2(x+1)`, `x^2 - 4x`, `sqrt(x)`) → expression SymPy en les seules `variables`."""
    text = (text or "").strip().replace("−", "-").replace("×", "*").replace("²", "^2").replace("³", "^3")
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    if not text:
        raise ExpressionError("Expression vide.")
    if len(text) > MAX_LENGTH:
        raise ExpressionError("Expression trop longue.")
    if not ALLOWED_CHARS_RE.match(text) or "__" in text:
        raise ExpressionError("Caractère non autorisé dans l'expression.")

    variables = set(variables)
    allowed = variables | FUNCTIONS.keys() | CONSTANTS.keys()
    for name in IDENTIFIER_RE.findall(text):
        # « xy » est lu x*y quand x et y sont des variables.
        if name not in allowed and not set(name) <= variables:
            expected = ", ".join(sorted(variables)) or "aucune variable"
            raise ExpressionError(f"« {name} » inconnu : variables attendues : {expected}.")

    local = {name: Symbol(name) for name in variables}
    try:
        expr = parse_expr(text, local_dict=local, global_dict=dict(SAFE_GLOBALS),
                          transformations=TRANSFORMATIONS, evaluate=False)
    except (SyntaxError, TokenError, TypeError, ValueError, AttributeError, NameError, ZeroDivisionError):
        raise ExpressionError("Expression illisible : vérifie les parenthèses et les opérateurs.")
    if not hasattr(expr, "atoms"):
        raise ExpressionError("Expression illisible.")
    _check_exponents(expr)
    return expr.doit()


def _check_exponents(expr):
    for power in expr.atoms(Pow):
        exponent = power.exp
        if exponent.free_symbols:
            continue
        if not exponent.is_Number or abs(exponent) > MAX_EXPONENT:
            raise ExpressionError("Exposant trop grand.")


def evaluate(expr, values):
    """Valeur complexe de l'expression, ou None si non définie en ce point."""
    try:
        result = complex(expr.evalf(subs=values))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        return None
    if cmath.isnan(result) or cmath.isinf(result):
        return None
    return result


def equivalent(a, b, variables):
    """Égalité par évaluation en points aléatoires (déterministes) : rapide et sans risque de blocage."""
    symbols = [Symbol(name) for name in sorted(variables)]
    rng = random.Random(0)
    compared = 0
    for _ in range(SAMPLES * 3):
        values = {s: rng.choice([-1, 1]) * rng.uniform(0.3, 3.7) for s in symbols}
        va, vb = evaluate(a, values), evaluate(b, values)
        if va is None and vb is None:
            continue
        if va is None or vb is None:
            return False
        if abs(va - vb) > 1e-8 * max(1.0, abs(va), abs(vb)):
            return False
        compared += 1
        if compared >= SAMPLES or not symbols:
            return True
    return compared > 0
