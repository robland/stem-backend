import pytest

from llm.clients import ImageInput
from llm.exceptions import LLMOutputInvalid
from llm.services import exam_for, extract_exercises, generate_exercise

from .factories import generated_exercise, step

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

    assert result.prompt_id == "extraction.v2"
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
    html = {"is_exercise_document": True, "exercises": [RESPONSE["exercises"][0] | {"statement": "<p>x</p>"}]}
    fake_llm.queue(html, html)

    with pytest.raises(LLMOutputInvalid):
        extract_exercises([IMAGE])
    assert len(fake_llm.calls) == 2


def test_extract_exercises_retries_with_errors(fake_llm):
    undelimited = {"is_exercise_document": True, "exercises": [RESPONSE["exercises"][0] | {"statement": "f(x) = x^2"}]}
    fake_llm.queue(undelimited, RESPONSE)

    result = extract_exercises([IMAGE])

    assert len(result.output.exercises) == 2
    retry = fake_llm.calls[1]["prompt"].user
    assert "Ta réponse précédente était invalide" in retry
    assert "hors de $...$" in retry
    assert "invalide" not in fake_llm.calls[0]["prompt"].user


def test_extraction_prompt_gives_priority_to_document_level(fake_llm):
    fake_llm.queue(RESPONSE)

    extract_exercises([IMAGE], declared_level="3e")

    system = fake_llm.calls[0]["prompt"].system
    assert "prime sur le niveau déclaré" in system
    assert "$\\mathbb{R}$" in system and "\\ce{CH4}" in system


class TestGenerateExercise:
    def generate(self):
        return generate_exercise(
            statement="Étudier les variations de $f(x) = x^2 - 4x + 3$.", subject="maths", level="3e",
            chapter="Fonctions",
        )

    def test_generate(self, fake_llm):
        fake_llm.queue(generated_exercise())

        result = self.generate()

        assert result.prompt_id == "generation.v3"
        prompt = fake_llm.calls[0]["prompt"]
        assert fake_llm.calls[0]["task"] == "generation"
        assert "élève de 3e qui prépare le BEPC" in prompt.system
        assert "sous la forme {{1}}, {{2}}" in prompt.system
        assert "$f(0) =$ {{1}} et $f(2) =$ {{2}}" in prompt.system
        assert "au moins une étape par question" in prompt.system
        assert "« expanded » pour développer et réduire" in prompt.system
        assert "Chapitre : Fonctions" in prompt.user
        assert "$f(x) = x^2 - 4x + 3$" in prompt.user
        assert "invalide" not in prompt.user

    def test_invalid_output_is_retried_once_with_errors(self, fake_llm):
        broken = generated_exercise(step(activity="mcq") | {"hints": ["un"]})
        fake_llm.queue(broken, generated_exercise())

        result = self.generate()

        assert result.output.title
        retry_prompt = fake_llm.calls[1]["prompt"].user
        assert "Ta réponse précédente était invalide" in retry_prompt
        assert "- steps.0.hints: Entre 3 et 3" in retry_prompt

    def test_second_invalid_output_fails(self, fake_llm):
        broken = generated_exercise(step() | {"hints": ["un"]})
        fake_llm.queue(broken, broken)

        with pytest.raises(LLMOutputInvalid):
            self.generate()
        assert len(fake_llm.calls) == 2

    def test_truncated_output_is_not_retried(self, fake_llm):
        fake_llm.queue(LLMOutputInvalid("tronquée"))

        with pytest.raises(LLMOutputInvalid):
            self.generate()
        assert len(fake_llm.calls) == 1

    def test_lycee_targets_bac(self):
        assert (exam_for("3e"), exam_for("Tle")) == ("BEPC", "BAC")


def test_generation_prompt_states_the_number_of_questions(fake_llm):
    fake_llm.queue(generated_exercise())

    generate_exercise(
        statement="Exercice 1\n1) Calculer $f(0)$.\n2) Factoriser.\n3) Résoudre.", subject="maths", level="3e",
    )

    user_prompt = fake_llm.calls[0]["prompt"].user
    assert "comporte 3 questions numérotées : le parcours doit avoir au moins 3 étapes" in user_prompt


def test_generation_prompt_without_numbered_questions(fake_llm):
    fake_llm.queue(generated_exercise())

    generate_exercise(statement="Résoudre $x^2 = 4$.", subject="maths", level="3e")

    assert "questions numérotées" not in fake_llm.calls[0]["prompt"].user
