"""Forme exigée d'une expression (`answer.form` des activités formula_input).

L'équivalence symbolique accepte `x^2 + 2x + x + 1` pour « développer et réduire » ;
ici on contrôle l'écriture de l'élève, sur l'expression non évaluée.
"""

import re
from math import gcd

from sympy import Add, Mul, Pow, Symbol, expand, factor, factor_list, preorder_traversal

from .symbolic import parse

FRACTION_RE = re.compile(r"^\s*([+-]?)\s*(\d+)\s*(?:/\s*(\d+))?\s*$")

FORM_MESSAGES = {
    "expanded": "C'est juste, mais l'expression doit être développée et réduite.",
    "factored": "C'est juste, mais l'expression doit être factorisée (écrite comme un produit).",
    "irreducible_fraction": "C'est juste, mais donne le résultat sous forme de fraction irréductible.",
}
NOT_FULLY_FACTORED = "C'est juste, mais la factorisation n'est pas terminée : un facteur se factorise encore."


def form_issue(text, form, variables):
    """Message pour l'élève si `text` n'est pas sous la forme `form`, sinon None.

    Lève ExpressionError si `text` est illisible.
    """
    if form == "any":
        return None
    if form == "irreducible_fraction":
        return None if _is_irreducible_fraction(text) else FORM_MESSAGES[form]
    raw = parse(text, variables, evaluate=False)
    if form == "expanded":
        return None if _is_expanded(raw) else FORM_MESSAGES[form]
    if form == "factored":
        if raw.is_Add:
            return FORM_MESSAGES[form]
        return None if _fully_factored(raw, variables) else NOT_FULLY_FACTORED
    raise ValueError(f"Forme inconnue : {form}")


def rewrite(source, form, variables):
    """`source` réécrite sous la forme `form` par SymPy (texte ASCII), ou None si impossible.

    Le LLM calcule mal (développements faux ou non réduits) ; SymPy ne se trompe pas.
    """
    expr = parse(source, variables)
    if form == "expanded":
        result = expand(expr)
    elif form == "factored":
        result = factor(expr)
    elif form == "irreducible_fraction" and expr.is_Rational:
        result = expr
    else:
        return None
    text = str(result).replace("**", "^")
    return text if form_issue(text, form, variables) is None else None


def _is_irreducible_fraction(text):
    match = FRACTION_RE.match((text or "").replace("−", "-"))
    if not match:
        return False
    numerator, denominator = int(match.group(2)), match.group(3)
    if denominator is None:
        return True
    denominator = int(denominator)
    return denominator > 1 and gcd(numerator, denominator) == 1


def _flatten(expr, kind):
    if isinstance(expr, kind):
        for arg in expr.args:
            yield from _flatten(arg, kind)
    else:
        yield expr


def _is_expanded(raw):
    """Somme de monômes sans parenthèses, chaque monôme écrit une fois (termes semblables regroupés)."""
    terms = list(_flatten(raw, Add))
    keys = []
    for term in terms:
        if any(isinstance(node, Add) for node in preorder_traversal(term)) or not _is_reduced_monomial(term):
            return False
        value = term.doit()
        if value == 0 and len(terms) > 1:
            return False
        keys.append(value.as_coeff_Mul()[1])
    return len(keys) == len(set(keys))


def _is_reduced_monomial(term):
    """Un seul coefficient (`3x/2` permis, `2*3x` non) et chaque base une seule fois (`x*x` non)."""
    factors = list(_flatten(term, Mul))
    integers = [f for f in factors if f.is_Integer and f != -1]
    fractions = [
        f for f in factors
        if (f.is_Rational and not f.is_Integer) or (isinstance(f, Pow) and f.base.is_Integer and f.exp == -1)
    ]
    others = [f for f in factors if f.is_Integer is not True and f not in fractions]
    bases = [f.base if isinstance(f, Pow) else f for f in others]
    return len(integers) <= 1 and len(fractions) <= 1 and len(bases) == len(set(bases))


def _fully_factored(raw, variables):
    """Aucun facteur polynomial ne se factorise encore sur les rationnels (`2(x^2 - 1)` non)."""
    symbols = [Symbol(name) for name in variables]
    if not symbols:
        return True
    for factor in _flatten(raw, Mul):
        base = factor.base if isinstance(factor, Pow) else factor
        if not isinstance(base, Add):
            continue
        polynomial = base.doit()
        if not polynomial.is_polynomial(*symbols):
            continue
        _, factors = factor_list(polynomial, *symbols)
        if sum(multiplicity for _, multiplicity in factors) > 1:
            return False
    return True
