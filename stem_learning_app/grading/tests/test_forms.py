import pytest

from grading.engine import grade_step
from grading.forms import FORM_MESSAGES, NOT_FULLY_FACTORED, form_issue, rewrite
from grading.symbolic import ExpressionError
from grading.verify import repair_forms, verify_exercise
from llm.schemas import GeneratedExercise
from llm.tests.factories import generated_exercise, step


@pytest.mark.parametrize(
    "text, expected",
    [
        ("x^2 + 5x + 6", True),
        ("6 + 5x + x^2", True),
        ("x^2 - 4x + 3", True),
        ("3x/2 - 1", True),
        ("3 + 2sqrt(2)", True),
        ("x^2 + 3x + 2x + 6", False),  # termes semblables
        ("(x + 2)(x + 3)", False),
        ("x(x + 5) + 6", False),
        ("x*x + 5x + 6", False),
        ("2*3x + 1", False),
        ("x^2 + 5x + 6 + 0", False),
    ],
)
def test_expanded(text, expected):
    assert (form_issue(text, "expanded", ["x"]) is None) is expected


@pytest.mark.parametrize(
    "text, message",
    [
        ("(x - 1)(x + 3)", None),
        ("(x + 1)^2", None),
        ("-(x - 1)(x + 1)", None),
        ("3(x + 2)", None),
        ("(x^2 + 1)(x - 2)", None),  # x^2 + 1 irréductible sur Q
        ("x^2 + 2x - 3", FORM_MESSAGES["factored"]),
        ("x(x + 2) - 3", FORM_MESSAGES["factored"]),
        ("2(x^2 - 1)", NOT_FULLY_FACTORED),
    ],
)
def test_factored(text, message):
    assert form_issue(text, "factored", ["x"]) == message


@pytest.mark.parametrize(
    "text, expected",
    [("3/4", True), ("-3/4", True), (" 7 ", True), ("6/8", False), ("6/3", False), ("4/1", False), ("0.75", False)],
)
def test_irreducible_fraction(text, expected):
    assert (form_issue(text, "irreducible_fraction", []) is None) is expected


@pytest.mark.parametrize(
    "source, form, variables, expected",
    [
        ("(2*x + 3)^2 - (x - 1)*(x + 5)", "expanded", ["x"], "3*x^2 + 8*x + 14"),
        ("x^2 - 4*x + 3", "factored", ["x"], "(x - 3)*(x - 1)"),
        ("1/2 + 1/4", "irreducible_fraction", [], "3/4"),
        ("sqrt(2)", "irreducible_fraction", [], None),
    ],
)
def test_rewrite(source, form, variables, expected):
    assert rewrite(source, form, variables) == expected


def test_any_form_and_unreadable_text():
    assert form_issue("x + x", "any", ["x"]) is None
    with pytest.raises(ExpressionError):
        form_issue("x +", "expanded", ["x"])


def expand_step(mistakes=()):
    data = step(common_mistakes=list(mistakes))
    data["activity"]["prompt"] = "Développe et réduis : $(x + 2)(x + 3) = \\placeholder{}$"
    data["activity"]["answer"] = {"expression": "x^2 + 5*x + 6", "variables": ["x"], "form": "expanded",
                                 "source": "(x + 2)*(x + 3)"}
    return data


class TestGrading:
    def test_expected_form_is_correct(self):
        assert grade_step(expand_step(), {"expression": "x^2+5x+6"}).is_correct

    def test_equivalent_but_wrong_form(self):
        result = grade_step(expand_step(), {"expression": "x^2 + 3x + 2x + 6"})

        assert not result.is_correct
        assert result.feedback == FORM_MESSAGES["expanded"]
        assert result.details == {"form": False}

    def test_form_mistake_needs_the_same_writing(self):
        mistakes = [{"pattern": "x^2 + 3x + 2x + 6", "feedback": "Regroupe $3x$ et $2x$."}]

        assert grade_step(expand_step(mistakes), {"expression": "x^2+3*x+2x+6"}).feedback == "Regroupe $3x$ et $2x$."
        # Autre forme non réduite : feedback de forme, pas celui de l'erreur typique.
        assert grade_step(expand_step(mistakes), {"expression": "(x+2)(x+3)"}).feedback == FORM_MESSAGES["expanded"]

    def test_wrong_value_is_not_a_form_issue(self):
        result = grade_step(expand_step(), {"expression": "x^2 + 6"})

        assert not result.is_correct
        assert result.details == {}


class TestVerification:
    def verify(self, data):
        return verify_exercise(GeneratedExercise.model_validate(generated_exercise(data)))

    def test_non_conforming_equivalent_mistake_is_legitimate(self):
        assert self.verify(expand_step([{"pattern": "x^2 + 3x + 2x + 6", "feedback": "Réduis."}])) == []

    def test_conforming_equivalent_mistake_is_an_issue(self):
        [issue] = self.verify(expand_step([{"pattern": "6 + 5x + x^2", "feedback": "?"}]))

        assert "équivaut à la bonne réponse" in issue

    def test_expected_answer_must_have_the_form(self):
        data = expand_step()
        data["activity"]["answer"]["expression"] = "(x + 2)*(x + 3)"

        [issue] = self.verify(data)

        assert "n'est pas sous la forme expanded" in issue

    def test_expected_answer_must_equal_the_source(self):
        # Erreur réelle de l'essai du 2026-11-07 : (2x+3)^2 - (x-1)(x+5) = 3x^2 + 8x + 14.
        data = expand_step()
        data["activity"]["answer"] |= {"source": "(2*x + 3)^2 - (x - 1)*(x + 5)", "expression": "3*x^2 + 10*x + 8"}

        [issue] = self.verify(data)

        assert "n'est pas égale à l'expression de départ" in issue
        assert "le bon résultat est « 3*x^2 + 8*x + 14 »" in issue
        data["activity"]["answer"]["expression"] = "3*x^2 + 8*x + 14"
        assert self.verify(data) == []

    def test_correct_but_unreduced_answer_is_rewritten(self):
        data = expand_step([{"pattern": "x^2 + 3x + 2x + 6", "feedback": "Réduis."}])
        data["activity"]["answer"]["expression"] = "x^2 + 2*x + 3*x + 6"
        content = GeneratedExercise.model_validate(generated_exercise(data))

        [repair] = repair_forms(content)

        assert content.steps[0].activity.answer.expression == "x^2 + 5*x + 6"
        assert "→ « x^2 + 5*x + 6 »" in repair
        assert verify_exercise(content) == []

    def test_wrong_answer_is_not_repaired(self):
        data = expand_step()
        data["activity"]["answer"]["expression"] = "x^2 + 6*x + 6"
        content = GeneratedExercise.model_validate(generated_exercise(data))

        assert repair_forms(content) == []
        assert content.steps[0].activity.answer.expression == "x^2 + 6*x + 6"

    def test_unreadable_source(self):
        data = expand_step()
        data["activity"]["answer"]["source"] = "(x + 2)(x +"

        [issue] = self.verify(data)

        assert "answer.source illisible" in issue
