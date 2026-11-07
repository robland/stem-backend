"""Revérification d'un parcours généré par les moteurs de calcul (README §5).

Les validateurs Pydantic garantissent la cohérence interne ; ici on vérifie la
justesse : expressions lisibles, points sur la courbe, signe de la dérivée,
conservation des atomes, conversions d'unités. Chaque problème est décrit pour
une régénération ciblée.
"""

import re

from sympy import Symbol, diff, oo

from llm.statement import count_questions

from .chemistry import FormulaError, balance_report, is_simplest, parse_formula
from .forms import form_issue, rewrite
from .symbolic import ExpressionError, equivalent, evaluate, parse
from .units import UnitError, convert

INFINITY_RE = re.compile(r"^([+-]?)(\\infty|∞|inf)$")


def verify_exercise(exercise):
    """`exercise` : GeneratedExercise ou ExerciseContent. Renvoie la liste des problèmes détectés."""
    issues = _coverage(exercise)
    for index, step in enumerate(exercise.steps):
        checker = CHECKERS.get(step.activity.type)
        if checker:
            issues += [f"steps.{index}.activity ({step.activity.type}) : {issue}" for issue in checker(step)]
    return issues


def repair_forms(exercise):
    """Réécrit sous la forme exigée les réponses attendues justes mais mal écrites (ex. non réduites).

    Modifie `exercise` en place ; renvoie les réparations faites. Une réponse fausse n'est pas
    réparée : les indices et la correction rédigée reposent sur le même calcul, il faut régénérer.
    """
    repairs = []
    for index, step in enumerate(exercise.steps):
        activity = step.activity
        if activity.type != "formula_input" or activity.answer.form == "any" or not activity.answer.source:
            continue
        answer = activity.answer
        try:
            expected = parse(answer.expression, answer.variables)
            if (not form_issue(answer.expression, answer.form, answer.variables)
                    or not equivalent(parse(answer.source, answer.variables), expected, answer.variables)):
                continue
            rewritten = rewrite(answer.source, answer.form, answer.variables)
        except ExpressionError:
            continue
        if rewritten:
            repairs.append(f"steps.{index} : « {answer.expression} » → « {rewritten} »")
            answer.expression = rewritten
    return repairs


def _coverage(exercise):
    """Au moins une étape par question numérotée de l'énoncé (contenu stocké uniquement)."""
    statement = getattr(exercise, "statement", "")
    questions = count_questions(statement)
    if questions and len(exercise.steps) < questions:
        return [
            f"le parcours n'a que {len(exercise.steps)} étape(s) pour {questions} questions dans l'énoncé : "
            "au moins une étape par question, dans l'ordre"
        ]
    return []


def _formula_input(step):
    answer = step.activity.answer
    try:
        expected = parse(answer.expression, answer.variables)
    except ExpressionError as e:
        return [f"answer.expression illisible ({e})"]
    issues = []
    if answer.source:
        try:
            if not equivalent(parse(answer.source, answer.variables), expected, answer.variables):
                issues.append(
                    f"answer.expression « {answer.expression} » n'est pas égale à l'expression de départ "
                    f"« {answer.source} » : refaire le calcul"
                )
        except ExpressionError as e:
            issues.append(f"answer.source illisible ({e})")
    if form_issue(answer.expression, answer.form, answer.variables):
        issues.append(f"answer.expression « {answer.expression} » n'est pas sous la forme {answer.form}")
    for mistake in step.common_mistakes:
        try:
            # Une forme équivalente mais non conforme (ex. non réduite) est une erreur typique légitime.
            if (equivalent(parse(mistake.pattern, answer.variables), expected, answer.variables)
                    and not form_issue(mistake.pattern, answer.form, answer.variables)):
                issues.append(f"l'erreur typique « {mistake.pattern} » équivaut à la bonne réponse")
        except ExpressionError:
            continue
    return issues


def _graph_points(step):
    activity = step.activity
    try:
        function = parse(activity.answer.function, ["x"])
    except ExpressionError as e:
        return [f"answer.function illisible ({e})"]
    issues = []
    for point in activity.answer.points:
        value = evaluate(function, {Symbol("x"): point.x})
        if value is None or abs(value.imag) > 1e-9 or abs(value.real - point.y) > activity.tolerance / 2:
            issues.append(f"le point ({point.x}, {point.y}) n'est pas sur la courbe de {activity.answer.function}")
    return issues


def _graph_parameters(step):
    activity = step.activity
    names = [slider.name for slider in activity.sliders]
    try:
        parse(activity.function, ["x", *names])
    except ExpressionError as e:
        return [f"function illisible ({e})"]
    sliders = {slider.name: slider for slider in activity.sliders}
    return [
        f"la valeur attendue de {v.name} ({v.value}) est hors du curseur [{sliders[v.name].min}, {sliders[v.name].max}]"
        for v in activity.answer.values
        if not sliders[v.name].min <= v.value <= sliders[v.name].max
    ]


def _variation_table(step):
    activity = step.activity
    if not activity.answer.function:
        return []
    try:
        function = parse(activity.answer.function, ["x"])
    except ExpressionError as e:
        return [f"answer.function illisible ({e})"]
    bounds = [_parse_bound(value) for value in activity.x_values]
    if any(bound is None for bound in bounds):
        return []  # Valeurs non numériques (ex. « \frac{1}{2} ») : vérification impossible, pas une erreur.
    if bounds != sorted(bounds):
        return ["x_values doit être rangé dans l'ordre croissant"]

    x = Symbol("x")
    derivative = diff(function, x)
    issues = []
    for index, (left, right, sign) in enumerate(zip(bounds, bounds[1:], activity.answer.signs)):
        value = evaluate(derivative, {x: _inside(left, right)})
        if value is None or abs(value.real) < 1e-12:
            continue
        actual = "+" if value.real > 0 else "-"
        if actual != sign:
            issues.append(f"sur l'intervalle {index + 1}, la dérivée est de signe {actual}, pas {sign}")
    return issues


def _parse_bound(text):
    text = text.strip().strip("$").strip()
    match = INFINITY_RE.match(text)
    if match:
        return -oo if match.group(1) == "-" else oo
    try:
        value = parse(text, [])
    except ExpressionError:
        return None
    return value if value.is_real else None


def _inside(left, right):
    if left == -oo and right == oo:
        return 0
    if left == -oo:
        return float(right) - 1
    if right == oo:
        return float(left) + 1
    return (float(left) + float(right)) / 2


def _chem_balance(step):
    activity = step.activity
    try:
        issues = balance_report(activity.reactants, activity.products, activity.answer.coefficients)
    except FormulaError as e:
        return [str(e)]
    if not issues and not is_simplest(activity.answer.coefficients):
        issues.append("les coefficients attendus ne sont pas les plus petits entiers")
    return issues


def _chem_formula(step):
    try:
        parse_formula(step.activity.answer.formula)
    except FormulaError as e:
        return [str(e)]
    return []


def _unit_conversion(step):
    activity = step.activity
    try:
        expected = convert(activity.value, activity.from_unit, activity.to_unit)
    except UnitError:
        return []  # Unité hors de la table : vérification impossible, pas une erreur.
    margin = max(activity.tolerance, 1e-9) * abs(expected)
    if abs(activity.answer.value - expected) > margin:
        return [f"{activity.value} {activity.from_unit} = {expected:g} {activity.to_unit}, pas {activity.answer.value:g}"]
    return []


CHECKERS = {
    "formula_input": _formula_input,
    "graph_points": _graph_points,
    "graph_parameters": _graph_parameters,
    "variation_table": _variation_table,
    "chem_balance": _chem_balance,
    "chem_formula": _chem_formula,
    "unit_conversion": _unit_conversion,
}
