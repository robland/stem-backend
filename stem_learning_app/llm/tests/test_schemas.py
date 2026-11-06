import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import ValidationError

from llm.schemas import ExtractionOutput
from llm.schemas.extraction import MAX_EXERCISES_PER_UPLOAD

# Mots-clés refusés par les structured outputs stricts d'OpenAI.
UNSUPPORTED_KEYWORDS = {"default", "minLength", "maxLength", "minItems", "maxItems"}


def exercise(**overrides):
    data = {
        "statement": "Résoudre $x^2 - 4 = 0$.",
        "subject": "maths",
        "level": "3e",
        "chapter_hint": "Équations",
    }
    return data | overrides


def walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def test_schema_is_compatible_with_strict_structured_outputs():
    schema = to_strict_json_schema(ExtractionOutput)

    for node in walk(schema):
        assert not UNSUPPORTED_KEYWORDS & node.keys(), node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])


def test_valid_output():
    output = ExtractionOutput.model_validate({"is_exercise_document": True, "exercises": [exercise()]})

    assert output.exercises[0].subject == "maths"


def test_nullable_classification():
    output = ExtractionOutput.model_validate(
        {"is_exercise_document": True, "exercises": [exercise(subject=None, level=None, chapter_hint=None)]}
    )

    assert output.exercises[0].subject is None


def test_statement_is_stripped_and_keeps_latex_and_chemistry():
    statement = "  Équilibrer \\ce{H2 + O2 -> H2O} puis montrer que $a<b$ et $x < 3$.  "
    output = ExtractionOutput.model_validate(
        {"is_exercise_document": True, "exercises": [exercise(statement=statement)]}
    )

    assert output.exercises[0].statement == statement.strip()


@pytest.mark.parametrize("statement", ["<p>Calculer</p>", "Calculer<br>", "<script>alert(1)</script>", "<IMG src=x>"])
def test_html_is_rejected(statement):
    with pytest.raises(ValidationError, match="HTML"):
        ExtractionOutput.model_validate({"is_exercise_document": True, "exercises": [exercise(statement=statement)]})


@pytest.mark.parametrize(
    "overrides",
    [
        {"subject": "philosophie"},
        {"level": "CM2"},
        {"statement": "   "},
        {"statement": "x" * 5001},
        {"chapter_hint": "x" * 201},
        {"extra": "champ inattendu"},
    ],
)
def test_invalid_exercise_is_rejected(overrides):
    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate({"is_exercise_document": True, "exercises": [exercise(**overrides)]})


def test_too_many_exercises_is_rejected():
    with pytest.raises(ValidationError, match="Plus de"):
        ExtractionOutput.model_validate(
            {"is_exercise_document": True, "exercises": [exercise()] * (MAX_EXERCISES_PER_UPLOAD + 1)}
        )


def test_missing_field_is_rejected():
    data = exercise()
    del data["chapter_hint"]

    with pytest.raises(ValidationError):
        ExtractionOutput.model_validate({"is_exercise_document": True, "exercises": [data]})
