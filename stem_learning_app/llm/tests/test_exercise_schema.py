import copy

import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import ValidationError

from llm.content_schema import CONTENT_SCHEMA_PATH, content_json_schema
from llm.schemas import ExerciseContent, GeneratedExercise
from llm.schemas.exercise import ACTIVITY_TYPES

from .factories import ACTIVITIES, generated_exercise, step
from .test_schemas import UNSUPPORTED_KEYWORDS, walk


def validate(data):
    return GeneratedExercise.model_validate(data)


def with_activity(name, **changes):
    activity = copy.deepcopy(ACTIVITIES[name])
    for key, value in changes.items():
        if "." in key:
            outer, inner = key.split(".")
            activity[outer][inner] = value
        else:
            activity[key] = value
    return generated_exercise(step(activity=name) | {"activity": activity})


def test_schema_is_compatible_with_strict_structured_outputs():
    schema = to_strict_json_schema(GeneratedExercise)

    for node in walk(schema):
        assert not UNSUPPORTED_KEYWORDS & node.keys(), node
        assert "oneOf" not in node and "discriminator" not in node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])


def test_factory_covers_every_activity_type():
    assert set(ACTIVITIES) == {cls.model_fields["type"].annotation.__args__[0] for cls in ACTIVITY_TYPES}


@pytest.mark.parametrize("name", sorted(ACTIVITIES))
def test_each_activity_type_is_valid(name):
    exercise = validate(generated_exercise(step(activity=name)))

    assert exercise.steps[0].activity.type == name


def test_content_adds_statement_and_version():
    content = ExerciseContent.model_validate(
        generated_exercise() | {"schema_version": "1.1", "statement": "Étudier $f$."}
    )

    assert content.schema_version == "1.1"


def test_committed_json_schema_is_up_to_date():
    assert CONTENT_SCHEMA_PATH.read_text(encoding="utf-8") == content_json_schema(), (
        "Lancer : python manage.py export_content_schema"
    )


@pytest.mark.parametrize(
    "name, changes, message",
    [
        ("mcq", {"answer.option_ids": ["z"]}, "options existantes"),
        ("mcq", {"answer.option_ids": ["a", "b"]}, "Une seule bonne réponse"),
        ("mcq", {"options": [{"id": "a", "content": "1"}]}, "Entre 2 et 6"),
        ("mcq", {"options": [{"id": "a", "content": "1"}, {"id": "a", "content": "2"}]}, "double"),
        ("short_answer", {"answer.value": None}, "numérique"),
        ("short_answer", {"grading": "normalized_text"}, "au moins une réponse"),
        ("fill_blanks", {"text": "Sans trou."}, "aucun trou"),
        ("fill_blanks", {"text": "{{1}} puis {{1}}", "answer.blanks": [{"id": "1", "accepted": ["2"]}]},
         "numéro différent"),
        ("fill_blanks", {"answer.blanks": [{"id": "1", "accepted": ["2"]}]}, "exactement les trous"),
        ("matching", {"answer.pairs": [{"left_id": "l1", "right_id": "r1"}]}, "exactement une fois"),
        ("matching", {"answer.pairs": [{"left_id": "l1", "right_id": "r1"}, {"left_id": "l2", "right_id": "r9"}]},
         "inexistant"),
        ("ordering", {"answer.order": ["i1"]}, "permutation"),
        ("formula_input", {"prompt": "$\\placeholder{} = \\placeholder{}$"}, "placeholder"),
        ("formula_input", {"answer.form": "reduced"}, "form"),
        ("formula_input", {"answer.form": "expanded"}, "answer.source est obligatoire"),
        ("graph_points", {"answer.points": [{"x": 0, "y": 3}]}, "un point par abscisse"),
        ("graph_points", {"axes": {"x_min": 5, "x_max": 1, "y_min": 0, "y_max": 1}}, "Bornes"),
        ("graph_parameters", {"answer.values": [{"name": "a", "value": 2}]}, "une valeur par curseur"),
        ("variation_table", {"answer.arrows": ["up", "up"]}, "signe de la dérivée"),
        ("variation_table", {"answer.signs": ["-"]}, "par intervalle"),
        ("chem_balance", {"answer.coefficients": [2, 1]}, "Un coefficient"),
        ("chem_balance", {"answer.coefficients": [2, 0, 2]}, "≥ 1"),
        ("unit_conversion", {"tolerance": 5}, "relative"),
    ],
)
def test_inconsistent_activity_is_rejected(name, changes, message):
    with pytest.raises(ValidationError, match=message):
        validate(with_activity(name, **changes))


@pytest.mark.parametrize(
    "content, expected",
    [
        ("(a + b)^2 = a^2 + 2ab + b^2", "$(a + b)^2 = a^2 + 2ab + b^2$"),
        ("\\frac{a}{b} \\times c", "$\\frac{a}{b} \\times c$"),
        ("$(x^n)' = n x^{n-1}$", "$(x^n)' = n x^{n-1}$"),
    ],
)
def test_bare_recall_formula_is_delimited(content, expected):
    data = generated_exercise(recall=[{"kind": "formula", "content": content, "explanation": "Rappel."}])

    assert validate(data).recall[0].content == expected


@pytest.mark.parametrize(
    "recall",
    [
        {"kind": "formula", "content": "Pour tout a : (a + b)^2 = a^2 + 2ab + b^2", "explanation": "Rappel."},
        {"kind": "property", "content": "(a + b)^2 = a^2 + 2ab + b^2", "explanation": "Rappel."},
    ],
)
def test_recall_with_text_is_not_rewritten(recall):
    with pytest.raises(ValidationError, match="hors de"):
        validate(generated_exercise(recall=[recall]))


def test_missing_placeholder_is_added():
    exercise = validate(with_activity("formula_input", prompt="Développe et réduis $A$."))

    assert exercise.steps[0].activity.prompt == "Développe et réduis $A$.\n$\\placeholder{}$"


def test_error_location_names_the_activity_type():
    with pytest.raises(ValidationError) as excinfo:
        validate(with_activity("mcq", **{"answer.option_ids": ["z"]}))

    [error] = excinfo.value.errors()
    assert error["loc"][:4] == ("steps", 0, "activity", "mcq")


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"hints": ["un", "deux"]}, "Entre 3 et 3"),
        ({"id": "etape1"}, "pattern"),
        ({"skill": "Dérivée"}, "pattern"),
        ({"explanation": "<p>Correction</p>"}, "HTML"),
    ],
)
def test_invalid_step_is_rejected(overrides, message):
    with pytest.raises(ValidationError, match=message):
        validate(generated_exercise(step() | overrides))


def test_duplicate_step_ids_are_rejected():
    with pytest.raises(ValidationError, match="étapes en double"):
        validate(generated_exercise(step("s1"), step("s1")))


def test_unknown_activity_type_is_rejected():
    with pytest.raises(ValidationError):
        validate(generated_exercise(step() | {"activity": {"type": "dessin", "prompt": "x"}}))


def test_fill_blanks_tolerates_spaces_inside_braces():
    exercise = validate(with_activity("fill_blanks", text="Abscisse {{ 1 }} et ordonnée {{2 }}."))

    assert exercise.steps[0].activity.text == "Abscisse {{1}} et ordonnée {{2}}."


@pytest.mark.parametrize(
    "text",
    ["Calcule f(x) = x² - 4x.", "Le méthane CH₄ brûle.", "Développe (2x + 3)².", "Calcule f(x) = x^2 - 4x.", "Résoudre dans \\mathbb{R}.", "Le méthane CH_4 brûle.", "Calcule \\frac{1}{2}."],
)
def test_math_outside_dollars_is_rejected_in_llm_output(text):
    with pytest.raises(ValidationError, match="hors de"):
        validate(generated_exercise(step() | {"objective": text}))


@pytest.mark.parametrize(
    "text",
    [
        "Calcule $f(x) = x^2 - 4x$ dans $\\mathbb{R}$.",
        "Équilibre \\ce{CH4 + 2O2 -> CO2 + 2H2O}.",
        "Le sulfate \\ce{SO4^{2-}} et $$\\frac{1}{2}$$.",
        "Une vitesse de 72 km/h, un volume de 2,5 cm³, une aire de 3 m².",
    ],
)
def test_delimited_math_is_accepted(text):
    validate(generated_exercise(step() | {"objective": text}))


def test_stored_statement_stays_lenient():
    """L'énoncé stocké est celui validé par l'élève, qui peut taper « x^2 » sans $...$."""
    content = ExerciseContent.model_validate(
        generated_exercise() | {"schema_version": "1.1", "statement": "Résoudre x^2 = 4."}
    )

    assert content.statement == "Résoudre x^2 = 4."
