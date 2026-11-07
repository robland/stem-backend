import pytest
from openai.lib._pydantic import to_strict_json_schema
from pydantic import ValidationError

from llm.prompts import latest_prompt
from llm.schemas import ModerationOutput
from llm.services import moderate_statement
from llm.tests.test_schemas import UNSUPPORTED_KEYWORDS, walk


def test_schema_is_compatible_with_strict_structured_outputs():
    for node in walk(to_strict_json_schema(ModerationOutput)):
        assert not UNSUPPORTED_KEYWORDS & node.keys(), node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False


@pytest.mark.parametrize(
    "data",
    [
        {"acceptable": True, "reasons": ["inappropriate"]},
        {"acceptable": False, "reasons": []},
        {"acceptable": False, "reasons": ["personal_data", "personal_data"]},
        {"acceptable": False, "reasons": ["spam"]},
    ],
)
def test_verdict_must_be_consistent(data):
    with pytest.raises(ValidationError):
        ModerationOutput.model_validate(data)


def test_moderate_statement(fake_llm):
    fake_llm.queue({"acceptable": False, "reasons": ["personal_data"]})

    result = moderate_statement("Exercice de Jean Mabiala, lycée Savorgnan : résoudre $x + 1 = 0$.")

    assert result.output.reasons == ["personal_data"]
    call = fake_llm.calls[0]
    assert (call["task"], call["prompt"].id) == ("moderation", latest_prompt("moderation").id)
    assert "Jean Mabiala" in call["prompt"].user
