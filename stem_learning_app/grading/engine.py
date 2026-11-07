"""Correction d'une réponse d'élève à une étape (README §5).

Le serveur est la source de vérité : ces règles sont à reproduire à l'identique
côté client pour la correction hors-ligne (cf. frontend/README.md).
"""

from dataclasses import dataclass, field
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llm.schemas.exercise import Step

from .chemistry import FormulaError, balance_report, is_simplest, normalize_formula, parse_formula
from .forms import form_issue
from .symbolic import ExpressionError, equivalent, parse
from .text import close_enough, normalize_text, parse_number

FEEDBACK_WRONG = "Ce n'est pas encore ça. Relis la consigne ou demande un indice."

Text = Annotated[str, Field(max_length=500)]
NumberInput = float | Annotated[str, Field(max_length=50)]


@dataclass(frozen=True)
class GradeResult:
    is_correct: bool
    feedback: str | None = None
    # Détail par élément (trous, points…) pour surligner ce qui est faux côté client.
    details: dict = field(default_factory=dict)


class InvalidResponse(ValueError):
    """Réponse mal formée pour ce type d'activité (erreur du client, pas de l'élève)."""


# --- Formats de réponse attendus, par type d'activité --------------------------------

class Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McqResponse(Response):
    option_ids: list[Annotated[str, Field(max_length=20)]] = Field(max_length=10)


class TrueFalseResponse(Response):
    value: bool


class TextResponse(Response):
    text: Text


class BlankResponse(Response):
    id: Annotated[str, Field(max_length=20)]
    text: Text


class FillBlanksResponse(Response):
    blanks: list[BlankResponse] = Field(max_length=20)


class PairResponse(Response):
    left_id: Annotated[str, Field(max_length=20)]
    right_id: Annotated[str, Field(max_length=20)]


class MatchingResponse(Response):
    pairs: list[PairResponse] = Field(max_length=20)


class OrderingResponse(Response):
    order: list[Annotated[str, Field(max_length=20)]] = Field(max_length=20)


class ExpressionResponse(Response):
    expression: Annotated[str, Field(max_length=200)]


class PointResponse(Response):
    x: float
    y: float


class GraphPointsResponse(Response):
    points: list[PointResponse] = Field(max_length=20)


class ParameterResponse(Response):
    name: Annotated[str, Field(max_length=10)]
    value: float


class GraphParametersResponse(Response):
    values: list[ParameterResponse] = Field(max_length=10)


class VariationTableResponse(Response):
    signs: list[Annotated[str, Field(max_length=1)]] = Field(max_length=10)
    arrows: list[Annotated[str, Field(max_length=4)]] = Field(max_length=10)


class ChemBalanceResponse(Response):
    coefficients: list[Annotated[int, Field(ge=0, le=99)]] = Field(max_length=10)


class FormulaResponse(Response):
    formula: Annotated[str, Field(max_length=100)]


class NumberResponse(Response):
    value: NumberInput


RESPONSE_MODELS = {
    "mcq": McqResponse,
    "true_false": TrueFalseResponse,
    "short_answer": TextResponse,
    "fill_blanks": FillBlanksResponse,
    "matching": MatchingResponse,
    "ordering": OrderingResponse,
    "formula_input": ExpressionResponse,
    "graph_points": GraphPointsResponse,
    "graph_parameters": GraphParametersResponse,
    "variation_table": VariationTableResponse,
    "chem_balance": ChemBalanceResponse,
    "chem_formula": FormulaResponse,
    "unit_conversion": NumberResponse,
}


# --- Point d'entrée ---------------------------------------------------------------

def grade_step(step, response):
    """`step` : dict ou Step (contenu complet, réponses comprises) ; `response` : dict envoyé par le client."""
    step = step if isinstance(step, Step) else Step.model_validate(step)
    activity = step.activity
    try:
        parsed = RESPONSE_MODELS[activity.type].model_validate(response)
    except ValidationError as e:
        raise InvalidResponse(f"Réponse invalide pour une activité {activity.type}.") from e

    result = GRADERS[activity.type](activity, parsed)
    if result.is_correct:
        return result
    # Une erreur typique prévue explique mieux que le feedback générique du moteur.
    mistake = _matching_mistake(step, parsed)
    return GradeResult(False, mistake or result.feedback or FEEDBACK_WRONG, result.details)


# --- Correcteurs ------------------------------------------------------------------

def _mcq(activity, response):
    return GradeResult(set(response.option_ids) == set(activity.answer.option_ids))


def _true_false(activity, response):
    return GradeResult(response.value == activity.answer.value)


def _short_answer(activity, response):
    answer = activity.answer
    if activity.grading == "numeric":
        text = response.text.strip()
        if answer.unit and text.endswith(answer.unit):
            text = text[: -len(answer.unit)]
        value = parse_number(text)
        if value is None:
            return GradeResult(False, "Écris un nombre (ex. 2,5).")
        return GradeResult(close_enough(value, answer.value, answer.tolerance))
    given = normalize_text(response.text)
    return GradeResult(given in {normalize_text(text) for text in answer.accepted})


def _fill_blanks(activity, response):
    given = {blank.id: normalize_text(blank.text) for blank in response.blanks}
    details = {
        blank.id: given.get(blank.id) in {normalize_text(text) for text in blank.accepted}
        for blank in activity.answer.blanks
    }
    return GradeResult(all(details.values()), details={"blanks": details})


def _matching(activity, response):
    expected = {(p.left_id, p.right_id) for p in activity.answer.pairs}
    given = {(p.left_id, p.right_id) for p in response.pairs}
    details = {left: (left, right) in given for left, right in expected}
    return GradeResult(given == expected, details={"pairs": details})


def _ordering(activity, response):
    return GradeResult(response.order == activity.answer.order)


def _formula_input(activity, response):
    variables = activity.answer.variables
    try:
        given = parse(response.expression, variables)
    except ExpressionError as e:
        return GradeResult(False, str(e))
    expected = parse(activity.answer.expression, variables)
    if not equivalent(given, expected, variables):
        return GradeResult(False)
    issue = form_issue(response.expression, activity.answer.form, variables)
    if issue:
        return GradeResult(False, issue, details={"form": False})
    return GradeResult(True)


def _graph_points(activity, response):
    tolerance = activity.tolerance
    remaining = list(response.points)
    details = {}
    for point in activity.answer.points:
        match = next(
            (p for p in remaining if close_enough(p.x, point.x, tolerance) and close_enough(p.y, point.y, tolerance)),
            None,
        )
        details[str(point.x)] = match is not None
        if match:
            remaining.remove(match)
    return GradeResult(all(details.values()) and not remaining, details={"points": details})


def _graph_parameters(activity, response):
    given = {v.name: v.value for v in response.values}
    details = {
        v.name: v.name in given and close_enough(given[v.name], v.value, activity.tolerance)
        for v in activity.answer.values
    }
    return GradeResult(all(details.values()), details={"values": details})


def _variation_table(activity, response):
    signs_ok = response.signs == activity.answer.signs
    arrows_ok = response.arrows == activity.answer.arrows
    return GradeResult(signs_ok and arrows_ok, details={"signs": signs_ok, "arrows": arrows_ok})


def _chem_balance(activity, response):
    try:
        issues = balance_report(activity.reactants, activity.products, response.coefficients)
    except FormulaError:
        issues = ["Équation illisible."]
    if issues:
        return GradeResult(False, issues[0])
    if not is_simplest(response.coefficients):
        return GradeResult(False, "L'équation est équilibrée, mais utilise les plus petits coefficients entiers.")
    return GradeResult(True)


def _chem_formula(activity, response):
    try:
        parse_formula(response.formula)
    except FormulaError as e:
        return GradeResult(False, str(e))
    # Comparaison stricte de l'écriture (casse comprise : Co ≠ CO).
    return GradeResult(normalize_formula(response.formula) == normalize_formula(activity.answer.formula))


def _unit_conversion(activity, response):
    value = parse_number(response.value)
    if value is None:
        return GradeResult(False, "Écris un nombre (ex. 2,5).")
    expected = activity.answer.value
    return GradeResult(close_enough(value, expected, activity.tolerance * abs(expected)))


GRADERS = {
    "mcq": _mcq,
    "true_false": _true_false,
    "short_answer": _short_answer,
    "fill_blanks": _fill_blanks,
    "matching": _matching,
    "ordering": _ordering,
    "formula_input": _formula_input,
    "graph_points": _graph_points,
    "graph_parameters": _graph_parameters,
    "variation_table": _variation_table,
    "chem_balance": _chem_balance,
    "chem_formula": _chem_formula,
    "unit_conversion": _unit_conversion,
}


# --- Erreurs typiques ----------------------------------------------------------------

def _matching_mistake(step, response):
    """Feedback de la première erreur typique qui correspond à la réponse (types à saisie libre)."""
    activity = step.activity
    for mistake in step.common_mistakes:
        if _same_as_pattern(activity, response, mistake.pattern):
            return mistake.feedback
    return None


def _same_as_pattern(activity, response, pattern):
    if activity.type == "formula_input":
        try:
            variables = activity.answer.variables
            target = parse(pattern, variables)
            if not equivalent(parse(response.expression, variables), target, variables):
                return False
            if activity.answer.form != "any" and equivalent(target, parse(activity.answer.expression, variables), variables):
                # Erreur de forme (ex. non réduite) : toute forme équivalente correspondrait, on exige la même écriture.
                return parse(response.expression, variables, evaluate=False) == parse(pattern, variables, evaluate=False)
            return True
        except ExpressionError:
            return False
    if activity.type == "short_answer":
        given, expected = parse_number(response.text), parse_number(pattern)
        if given is not None and expected is not None:
            return given == expected
        return normalize_text(response.text) == normalize_text(pattern)
    if activity.type == "unit_conversion":
        return parse_number(response.value) == parse_number(pattern)
    if activity.type == "chem_formula":
        return normalize_formula(response.formula) == normalize_formula(pattern)
    if activity.type == "mcq" and len(response.option_ids) == 1:
        option = next((o for o in activity.options if o.id == response.option_ids[0]), None)
        return option is not None and normalize_text(pattern) in {normalize_text(option.id), normalize_text(option.content)}
    return False
