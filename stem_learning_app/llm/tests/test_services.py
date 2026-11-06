import pytest

from llm.clients import ImageInput
from llm.exceptions import LLMOutputInvalid
from llm.services import extract_exercises

IMAGE = ImageInput(data=b"\xff\xd8", mime_type="image/jpeg")

RESPONSE = {
    "is_exercise_document": True,
    "exercises": [
        {
            "statement": "Exercice 1\na) Développer $(x+2)^2$.",
            "subject": "maths",
            "level": "3e",
            "chapter_hint": "Calcul littéral",
        },
        {
            "statement": "Exercice 2\nÉquilibrer \\ce{Fe + O2 -> Fe2O3}.",
            "subject": "physique_chimie",
            "level": None,
            "chapter_hint": None,
        },
    ],
}


def test_extract_exercises(fake_llm):
    fake_llm.queue(RESPONSE)

    result = extract_exercises([IMAGE], declared_level="Tle")

    assert result.prompt_id == "extraction.v1"
    assert [e.subject for e in result.output.exercises] == ["maths", "physique_chimie"]

    call = fake_llm.calls[0]
    assert call["task"] == "extraction"
    assert call["images"] == [IMAGE]
    assert "Niveau déclaré par l'élève : Terminale." in call["prompt"].user
    assert "physique_chimie (Physique-Chimie)" in call["prompt"].system
    assert "{{" not in call["prompt"].system


def test_extract_exercises_without_declared_level(fake_llm):
    fake_llm.queue({"is_exercise_document": False, "exercises": []})

    result = extract_exercises([IMAGE])

    assert result.output.is_exercise_document is False
    assert "non précisé" in fake_llm.calls[0]["prompt"].user


def test_extract_exercises_requires_images(fake_llm):
    with pytest.raises(ValueError):
        extract_exercises([])

    assert fake_llm.calls == []


def test_extract_exercises_rejects_html_output(fake_llm):
    fake_llm.queue({"is_exercise_document": True, "exercises": [RESPONSE["exercises"][0] | {"statement": "<p>x</p>"}]})

    with pytest.raises(LLMOutputInvalid):
        extract_exercises([IMAGE])
