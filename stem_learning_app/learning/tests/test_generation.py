from datetime import timedelta

import pytest
from django.utils import timezone

from curriculum.models import Subject
from ingestion.models import ExtractedExercise, Upload
from learning.models import Exercise
from learning.services import content_hash, public_content, run_generation
from llm.exceptions import LLMError, LLMRefusal
from llm.tests.factories import generated_exercise, step

pytestmark = pytest.mark.django_db

STATEMENT = "Étudier les variations de $f(x) = x^2 - 4x + 3$."


def make_extracted(user, statement=STATEMENT, subject="maths", validated=True, file_hash="h1"):
    upload = Upload.objects.create(
        user=user, file_type="image", file_size=1, file_hash=file_hash, status=Upload.Status.EXTRACTED
    )
    return ExtractedExercise.objects.create(
        upload=upload, order=0, statement=statement, subject=Subject.objects.get(code=subject), level="3e",
        validated_at=timezone.now() if validated else None,
    )


def generate_url(extracted):
    return f"/api/extracted-exercises/{extracted.id}/generate/"


@pytest.fixture
def generate(auth_client, fake_llm, django_capture_on_commit_callbacks):
    """Lance la génération (Celery eager) avec la réponse LLM donnée."""

    def _generate(extracted, *responses, client=auth_client):
        fake_llm.queue(*responses)
        with django_capture_on_commit_callbacks(execute=True):
            return client.post(generate_url(extracted))

    return _generate


class TestRequestGeneration:
    def test_generates_exercise(self, generate, auth_client, user, fake_llm):
        extracted = make_extracted(user)

        response = generate(extracted, generated_exercise())

        assert response.status_code == 202
        assert response.data["generation_status"] == Exercise.GenerationStatus.PENDING
        exercise = Exercise.objects.get()
        assert exercise.generation_status == Exercise.GenerationStatus.READY
        assert (exercise.owner, exercise.source, exercise.level, exercise.prompt_id) == (
            user, extracted, "3e", "generation.v3"
        )
        assert exercise.title == "Variations d'une fonction du second degré"
        assert exercise.content["statement"] == STATEMENT
        assert exercise.content["schema_version"] == exercise.schema_version == "1.1"
        assert exercise.content_hash == content_hash(STATEMENT, "maths", "3e")

    def test_requires_validated_statement(self, generate, user, fake_llm):
        response = generate(make_extracted(user, validated=False))

        assert response.status_code == 400
        assert "Valide l'énoncé" in str(response.data)
        assert fake_llm.calls == []

    def test_subject_not_open_yet(self, generate, user, fake_llm):
        response = generate(make_extracted(user, subject="histoire_geo"))

        assert response.status_code == 400
        assert "Histoire-Géographie" in str(response.data)

    def test_other_students_cannot_generate(self, generate, user, other_client):
        response = generate(make_extracted(user), client=other_client)

        assert response.status_code == 404

    def test_is_idempotent(self, generate, auth_client, user, fake_llm):
        extracted = make_extracted(user)
        first = generate(extracted, generated_exercise())

        second = auth_client.post(generate_url(extracted))

        assert second.status_code == 200
        assert second.data["id"] == first.data["id"]
        assert len(fake_llm.calls) == 1

    def test_failed_generation_can_be_relaunched(self, generate, user):
        extracted = make_extracted(user)
        first = generate(extracted, LLMError("timeout"))
        assert Exercise.objects.get().generation_status == Exercise.GenerationStatus.ERROR

        second = generate(extracted, generated_exercise())

        assert second.status_code == 202
        assert second.data["id"] == first.data["id"]
        assert Exercise.objects.get().generation_status == Exercise.GenerationStatus.READY

    def test_same_statement_reuses_cache(self, generate, user, other_user, other_client, fake_llm):
        generate(make_extracted(user), generated_exercise())
        # Même énoncé, casse et espaces différents, chez un autre élève.
        other = make_extracted(other_user, statement="  étudier les variations de $f(x) = x^2 - 4x + 3$. ")

        response = generate(other, client=other_client)

        assert response.status_code == 200
        assert response.data["generation_status"] == Exercise.GenerationStatus.READY
        copy = Exercise.objects.get(owner=other_user)
        assert copy.content["steps"] == Exercise.objects.get(owner=user).content["steps"]
        assert copy.prompt_id == ""
        assert len(fake_llm.calls) == 1

    def test_daily_quota(self, generate, user, settings):
        settings.GENERATION_DAILY_QUOTA = 1
        generate(make_extracted(user), generated_exercise())

        response = generate(make_extracted(user, statement="Autre énoncé $x$.", file_hash="h2"))

        assert response.status_code == 429
        assert int(response["Retry-After"]) > 0

    def test_cached_copies_do_not_count_toward_quota(self, generate, user, other_user, other_client, settings):
        settings.GENERATION_DAILY_QUOTA = 1
        generate(make_extracted(other_user), generated_exercise(), client=other_client)

        assert generate(make_extracted(user)).status_code == 200  # cache
        assert generate(make_extracted(user, statement="Autre $x$.", file_hash="h2"), generated_exercise()).status_code == 202

    def test_quota_resets_the_next_day(self, generate, user, settings):
        settings.GENERATION_DAILY_QUOTA = 1
        generate(make_extracted(user), generated_exercise())
        Exercise.objects.update(created_at=timezone.now() - timedelta(days=1))

        response = generate(make_extracted(user, statement="Autre $x$.", file_hash="h2"), generated_exercise())

        assert response.status_code == 202


class TestGenerationFailures:
    @pytest.mark.parametrize(
        "response, message",
        [(LLMError("timeout"), "a échoué"), (LLMRefusal("refus"), "ne peut pas être transformé")],
    )
    def test_failure_is_reported(self, generate, auth_client, user, response, message):
        exercise_id = generate(make_extracted(user), response).data["id"]

        detail = auth_client.get(f"/api/exercises/{exercise_id}/").data
        assert detail["generation_status"] == Exercise.GenerationStatus.ERROR
        assert message in detail["error_message"]
        assert detail["content"] is None

    def test_invalid_output_twice_is_an_error(self, generate, user):
        broken = generated_exercise(step() | {"hints": ["un"]})

        generate(make_extracted(user), broken, broken)

        assert Exercise.objects.get().generation_status == Exercise.GenerationStatus.ERROR

    def test_generation_runs_only_once(self, generate, user, fake_llm):
        generate(make_extracted(user), generated_exercise())

        run_generation(Exercise.objects.get().id)

        assert len(fake_llm.calls) == 1


class TestPublicContent:
    def test_answers_are_removed(self):
        content = generated_exercise(step("s1", "mcq"), step("s2", "chem_balance"))

        public = public_content(content)

        for public_step in public["steps"]:
            assert "answer" not in public_step["activity"]
            assert "common_mistakes" not in public_step and "explanation" not in public_step
            assert len(public_step["hints"]) == 2
        assert public["steps"][0]["activity"]["options"]
        # L'original n'est pas modifié.
        assert "answer" in content["steps"][0]["activity"]


def wrong_balance():
    """Parcours valide pour Pydantic mais faux en chimie (oxygène non conservé)."""
    data = step(activity="chem_balance")
    data["activity"]["answer"]["coefficients"] = [1, 1, 1]
    return generated_exercise(data)


class TestVerification:
    def test_wrong_answer_triggers_targeted_regeneration(self, generate, user, fake_llm):
        generate(make_extracted(user), wrong_balance(), generated_exercise())

        exercise = Exercise.objects.get()
        assert exercise.generation_status == Exercise.GenerationStatus.READY
        assert exercise.review_notes == ""
        assert len(fake_llm.calls) == 2
        retry = fake_llm.calls[1]["prompt"].user
        assert "Ta réponse précédente était invalide" in retry
        assert "atomes de O" in retry

    def test_still_wrong_goes_to_review(self, generate, auth_client, user, fake_llm):
        generate(make_extracted(user), wrong_balance(), wrong_balance())

        exercise = Exercise.objects.get()
        assert exercise.generation_status == Exercise.GenerationStatus.NEEDS_REVIEW
        assert "atomes de O" in exercise.review_notes
        assert len(fake_llm.calls) == 2
        detail = auth_client.get(f"/api/exercises/{exercise.id}/").data
        assert detail["content"] is None
        assert "vérifié" in detail["error_message"]
        assert "review_notes" not in detail

    def test_exercise_to_review_is_not_used_as_cache(self, generate, user, other_user, other_client, fake_llm):
        generate(make_extracted(user), wrong_balance(), wrong_balance())

        response = generate(make_extracted(other_user), generated_exercise(), client=other_client)

        assert response.status_code == 202
        assert len(fake_llm.calls) == 3

    def test_attempts_are_configurable(self, generate, user, fake_llm, settings):
        settings.GENERATION_ATTEMPTS = 1

        generate(make_extracted(user), wrong_balance())

        assert Exercise.objects.get().generation_status == Exercise.GenerationStatus.NEEDS_REVIEW
        assert len(fake_llm.calls) == 1


class TestCoverageRegeneration:
    def test_too_few_steps_triggers_regeneration(self, generate, user, fake_llm):
        statement = "Exercice 1\n1) Calculer $f(0)$.\n2) Calculer $f(2)$."
        generate(make_extracted(user, statement=statement), generated_exercise(step("s1")),
                 generated_exercise(step("s1"), step("s2", "mcq")))

        exercise = Exercise.objects.get()
        assert exercise.generation_status == Exercise.GenerationStatus.READY
        assert len(exercise.content["steps"]) == 2
        assert "1 étape(s) pour 2 questions" in fake_llm.calls[1]["prompt"].user
