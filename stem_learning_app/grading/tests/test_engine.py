import copy

import pytest

from grading.engine import FEEDBACK_WRONG, InvalidResponse, grade_step
from llm.tests.factories import ACTIVITIES, step


def make_step(activity, mistakes=None, **changes):
    data = step(activity=activity)
    for key, value in changes.items():
        outer, _, inner = key.partition(".")
        if inner:
            data["activity"][outer][inner] = value
        else:
            data["activity"][key] = value
    if mistakes is not None:
        data["common_mistakes"] = mistakes
    return data


CASES = [
    # (activité, réponse, correcte ?)
    ("mcq", {"option_ids": ["b"]}, True),
    ("mcq", {"option_ids": ["a"]}, False),
    ("true_false", {"value": True}, True),
    ("true_false", {"value": False}, False),
    ("short_answer", {"text": "3"}, True),
    ("short_answer", {"text": "3,0"}, True),
    ("short_answer", {"text": "4"}, False),
    ("fill_blanks", {"blanks": [{"id": "1", "text": " 2 "}, {"id": "2", "text": "-1"}]}, True),
    ("fill_blanks", {"blanks": [{"id": "1", "text": "2"}, {"id": "2", "text": "1"}]}, False),
    ("matching", {"pairs": [{"left_id": "l2", "right_id": "r2"}, {"left_id": "l1", "right_id": "r1"}]}, True),
    ("matching", {"pairs": [{"left_id": "l1", "right_id": "r2"}, {"left_id": "l2", "right_id": "r1"}]}, False),
    ("ordering", {"order": ["i1", "i2"]}, True),
    ("ordering", {"order": ["i2", "i1"]}, False),
    ("formula_input", {"expression": "2(x-2)"}, True),
    ("formula_input", {"expression": "2x"}, False),
    ("graph_points", {"points": [{"x": 2.1, "y": -0.9}, {"x": 0, "y": 3}]}, True),
    ("graph_points", {"points": [{"x": 0, "y": 3}]}, False),
    ("graph_points", {"points": [{"x": 0, "y": 3}, {"x": 2, "y": -1}, {"x": 4, "y": 3}]}, False),
    ("graph_parameters", {"values": [{"name": "a", "value": 2.2}, {"name": "b", "value": -1}]}, True),
    ("graph_parameters", {"values": [{"name": "a", "value": 1}, {"name": "b", "value": -1}]}, False),
    ("variation_table", {"signs": ["-", "+"], "arrows": ["down", "up"]}, True),
    ("variation_table", {"signs": ["+", "+"], "arrows": ["down", "up"]}, False),
    ("chem_balance", {"coefficients": [2, 1, 2]}, True),
    ("chem_balance", {"coefficients": [1, 1, 1]}, False),
    ("chem_formula", {"formula": "H₂O"}, True),
    ("chem_formula", {"formula": "HO2"}, False),
    ("unit_conversion", {"value": "2 500"}, True),
    ("unit_conversion", {"value": 2520}, True),  # tolérance relative 1 %
    ("unit_conversion", {"value": 250}, False),
]


@pytest.mark.parametrize("activity, response, expected", CASES)
def test_grading(activity, response, expected):
    result = grade_step(make_step(activity, mistakes=[]), response)

    assert result.is_correct is expected
    if not expected:
        assert result.feedback


def test_every_activity_type_is_covered():
    assert {case[0] for case in CASES} == set(ACTIVITIES)


@pytest.mark.parametrize(
    "activity, response",
    [
        ("mcq", {"option_ids": "b"}),
        ("mcq", {"value": True}),
        ("true_false", {}),
        ("chem_balance", {"coefficients": [2, "x"]}),
        ("formula_input", {"expression": "x" * 201}),
        ("ordering", {"order": ["i1"] * 21}),
    ],
)
def test_malformed_response(activity, response):
    with pytest.raises(InvalidResponse):
        grade_step(make_step(activity), response)


class TestFeedback:
    def test_common_mistake_formula_is_matched_symbolically(self):
        data = make_step("formula_input", mistakes=[{"pattern": "2x + 4", "feedback": "Attention au signe."}])

        result = grade_step(data, {"expression": "2(x+2)"})

        assert (result.is_correct, result.feedback) == (False, "Attention au signe.")

    def test_unknown_mistake_gets_generic_feedback(self):
        result = grade_step(make_step("formula_input"), {"expression": "x"})

        assert result.feedback == FEEDBACK_WRONG

    def test_unreadable_expression_explains_why(self):
        result = grade_step(make_step("formula_input"), {"expression": "2t"})

        assert not result.is_correct
        assert "variables attendues : x" in result.feedback

    def test_mcq_mistake_by_option_content(self):
        data = make_step("mcq", mistakes=[{"pattern": "1", "feedback": "C'est le degré de $f'$."}])

        assert grade_step(data, {"option_ids": ["a"]}).feedback == "C'est le degré de $f'$."

    def test_short_answer_mistake_by_number(self):
        data = make_step("short_answer", mistakes=[{"pattern": "-3", "feedback": "Signe !"}])

        assert grade_step(data, {"text": "-3,0"}).feedback == "Signe !"

    def test_chem_balance_names_the_unbalanced_element(self):
        result = grade_step(make_step("chem_balance"), {"coefficients": [2, 2, 2]})

        assert "atomes de O" in result.feedback

    def test_chem_balance_requires_smallest_coefficients(self):
        result = grade_step(make_step("chem_balance"), {"coefficients": [4, 2, 4]})

        assert not result.is_correct
        assert "plus petits coefficients" in result.feedback

    def test_short_answer_numeric_with_unit(self):
        data = make_step("short_answer", **{"answer.unit": "cm"})

        assert grade_step(data, {"text": "3 cm"}).is_correct

    def test_short_answer_text(self):
        data = make_step(
            "short_answer", grading="normalized_text",
            answer={"accepted": ["le sommet"], "value": None, "tolerance": None, "unit": None},
        )

        assert grade_step(data, {"text": "Le Sommet."}).is_correct
        assert not grade_step(data, {"text": "la base"}).is_correct

    def test_details_identify_wrong_blanks(self):
        result = grade_step(make_step("fill_blanks"), {"blanks": [{"id": "1", "text": "2"}, {"id": "2", "text": "0"}]})

        assert result.details == {"blanks": {"1": True, "2": False}}

    def test_missing_blank_is_wrong(self):
        result = grade_step(make_step("fill_blanks"), {"blanks": [{"id": "1", "text": "2"}]})

        assert result.details == {"blanks": {"1": True, "2": False}}


def test_does_not_modify_the_step():
    data = make_step("mcq")
    original = copy.deepcopy(data)

    grade_step(data, {"option_ids": ["a"]})

    assert data == original
