import copy

import pytest

from grading.verify import verify_exercise
from llm.schemas import GeneratedExercise
from llm.tests.factories import ACTIVITIES, generated_exercise, step


def verify(activity=None, mistakes=None, **changes):
    data = step(activity=activity or "formula_input")
    for key, value in changes.items():
        outer, _, inner = key.partition(".")
        if inner:
            data["activity"][outer][inner] = value
        else:
            data["activity"][key] = value
    if mistakes is not None:
        data["common_mistakes"] = mistakes
    return verify_exercise(GeneratedExercise.model_validate(generated_exercise(data)))


@pytest.mark.parametrize("name", sorted(ACTIVITIES))
def test_factory_activities_are_correct(name):
    assert verify(name) == []


def test_issue_mentions_step_and_type():
    [issue] = verify("chem_balance", **{"answer.coefficients": [1, 1, 1]})

    assert issue.startswith("steps.0.activity (chem_balance) : ")
    assert "atomes de O" in issue


@pytest.mark.parametrize(
    "activity, changes, mistakes, message",
    [
        ("formula_input", {"answer.expression": "2x +"}, None, "illisible"),
        ("formula_input", {}, [{"pattern": "2(x-2)", "feedback": "?"}], "équivaut à la bonne réponse"),
        ("graph_points", {"answer.points": [{"x": 0, "y": 3}, {"x": 2, "y": 1}]}, None, "pas sur la courbe"),
        ("graph_points", {"answer.function": "x^^2"}, None, "illisible"),
        ("graph_parameters", {"answer.values": [{"name": "a", "value": 5}, {"name": "b", "value": -1}]}, None,
         "hors du curseur"),
        ("graph_parameters", {"function": "a*x + c"}, None, "illisible"),
        ("variation_table", {"answer.signs": ["+", "-"], "answer.arrows": ["up", "down"]}, None, "signe -"),
        ("variation_table", {"x_values": ["$+\\infty$", "2", "$-\\infty$"]}, None, "ordre croissant"),
        ("chem_balance", {"answer.coefficients": [4, 2, 4]}, None, "plus petits entiers"),
        ("chem_balance", {"reactants": ["Xy", "O2"]}, None, "Élément inconnu"),
        ("chem_formula", {"answer.formula": "h2o"}, None, "illisible"),
        ("unit_conversion", {"answer.value": 250}, None, "2500"),
    ],
)
def test_detects_wrong_expected_answers(activity, changes, mistakes, message):
    issues = verify(activity, mistakes=mistakes, **changes)

    assert issues and message in issues[0]


def test_non_numeric_bounds_are_not_an_error():
    assert verify("variation_table", x_values=["$-\\infty$", "$\\frac{1}{2}$", "$+\\infty$"]) == []


def test_unknown_units_are_not_an_error():
    assert verify("unit_conversion", from_unit="°C", to_unit="K") == []


def test_variation_table_without_function_is_skipped():
    assert verify("variation_table", **{"answer.function": None, "answer.signs": ["+", "-"],
                                        "answer.arrows": ["up", "down"]}) == []


def test_does_not_modify_content():
    content = GeneratedExercise.model_validate(generated_exercise())
    before = copy.deepcopy(content.model_dump())

    verify_exercise(content)

    assert content.model_dump() == before
