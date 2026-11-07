from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from curriculum.models import Chapter, Subject
from ingestion.models import ExtractedExercise, Upload
from ingestion.services import purge_expired_files, run_extraction
from llm.exceptions import LLMError, LLMRefusal

from .factories import extracted, extraction_response, image_bytes, pdf_bytes

pytestmark = pytest.mark.django_db

UPLOADS_URL = "/api/uploads/"


def post_file(client, data, name="Jean_Dupont_devoir.jpg"):
    return client.post(UPLOADS_URL, {"file": SimpleUploadedFile(name, data)}, format="multipart")


def exercise_url(exercise, suffix=""):
    return f"/api/extracted-exercises/{exercise.id}/{suffix}"


@pytest.fixture
def send(auth_client, fake_llm, django_capture_on_commit_callbacks):
    """Envoie un document et exécute l'extraction (Celery eager) avec la réponse LLM donnée."""

    def _send(response, data=None, client=auth_client):
        fake_llm.queue(response)
        with django_capture_on_commit_callbacks(execute=True):
            result = post_file(client, data or image_bytes())
        return result

    return _send


@pytest.fixture
def extracted_upload(send, user):
    send(extraction_response(extracted(), extracted(statement="Exercice 2\nCalculer $3 \\times 4$.")))
    return Upload.objects.get(user=user)


@pytest.fixture
def chapter():
    return Chapter.objects.create(subject=Subject.objects.get(code="maths"), level="3e", name="Calcul littéral")


class TestCreateUpload:
    def test_requires_authentication(self, api_client):
        assert post_file(api_client, image_bytes()).status_code == 401

    def test_image_is_extracted(self, send, auth_client, fake_llm, user):
        response = send(extraction_response(extracted(), extracted(subject="physique_chimie", level=None)))

        assert response.status_code == 201
        assert response.data["status"] == Upload.Status.PENDING
        assert fake_llm.calls[0]["task"] == "extraction"

        detail = auth_client.get(f"{UPLOADS_URL}{response.data['id']}/").data
        assert detail["status"] == Upload.Status.EXTRACTED
        assert [(e["order"], e["subject"], e["level"]) for e in detail["exercises"]] == [
            (0, "maths", "3e"),
            (1, "physique_chimie", user.level),  # niveau absent → niveau de l'élève
        ]
        assert Upload.objects.get().prompt_id == "extraction.v2"

    def test_pdf_pages_are_sent_to_llm(self, send, fake_llm):
        response = send(extraction_response(extracted()), data=pdf_bytes(pages=2))

        assert response.data["file_type"] == Upload.FileType.PDF
        assert len(fake_llm.calls[0]["images"]) == 2

    def test_chapter_is_matched_from_hint(self, send, chapter):
        send(extraction_response(extracted(chapter_hint="calcul littéral"), extracted(chapter_hint="Inconnu")))

        first, second = ExtractedExercise.objects.order_by("order")
        assert first.chapter == chapter
        assert (second.chapter, second.chapter_hint) == (None, "Inconnu")

    def test_original_filename_is_not_stored(self, send):
        send(extraction_response(extracted()))

        name = Upload.objects.get().file.name
        assert "Jean" not in name and name.startswith("uploads/")

    def test_same_document_is_idempotent(self, send, auth_client, fake_llm):
        first = send(extraction_response(extracted()))
        second = post_file(auth_client, image_bytes())

        assert second.status_code == 200
        assert second.data["id"] == first.data["id"]
        assert len(fake_llm.calls) == 1

    def test_failed_document_can_be_sent_again(self, send):
        first = send(LLMError("timeout"))
        second = send(extraction_response(extracted()))

        assert second.status_code == 201
        assert second.data["id"] != first.data["id"]
        assert Upload.objects.get().status == Upload.Status.EXTRACTED

    def test_invalid_file_is_rejected(self, auth_client, fake_llm):
        response = post_file(auth_client, b"pas une image")

        assert response.status_code == 400
        assert "file" in response.data
        assert not Upload.objects.exists() and fake_llm.calls == []

    def test_too_large_file_is_rejected(self, auth_client, settings):
        settings.UPLOAD_MAX_BYTES = 100

        response = post_file(auth_client, image_bytes())

        assert response.status_code == 400
        assert "Mo maximum" in str(response.data["file"])

    def test_daily_quota(self, send, auth_client, settings):
        settings.UPLOAD_DAILY_QUOTA = 1
        send(extraction_response(extracted()))

        response = post_file(auth_client, image_bytes(color=(0, 0, 0)))

        assert response.status_code == 429
        assert int(response["Retry-After"]) > 0
        # Le renvoi d'un document déjà envoyé reste possible.
        assert post_file(auth_client, image_bytes()).status_code == 200

    def test_quota_resets_the_next_day(self, send, auth_client, settings):
        settings.UPLOAD_DAILY_QUOTA = 1
        send(extraction_response(extracted()))
        Upload.objects.update(created_at=timezone.now() - timedelta(days=1))

        assert send(extraction_response(extracted()), data=image_bytes(color=(0, 0, 0))).status_code == 201


class TestExtractionFailures:
    @pytest.mark.parametrize(
        "response, message",
        [
            (LLMError("timeout"), "L'analyse a échoué"),
            (LLMRefusal("refus"), "ne peut pas être analysé"),
            ({"is_exercise_document": False, "exercises": []}, "Aucun exercice détecté"),
        ],
    )
    def test_failure_is_reported_and_file_deleted(self, send, auth_client, response, message):
        upload_id = send(response).data["id"]

        detail = auth_client.get(f"{UPLOADS_URL}{upload_id}/").data
        assert detail["status"] == Upload.Status.ERROR
        assert message in detail["error_message"]
        assert detail["exercises"] == []
        assert not Upload.objects.get().file

    def test_extraction_runs_only_once(self, extracted_upload, fake_llm):
        run_extraction(extracted_upload.id)

        assert len(fake_llm.calls) == 1
        assert extracted_upload.exercises.count() == 2


class TestUploadAccess:
    def test_other_students_cannot_see_upload(self, extracted_upload, other_client):
        response = other_client.get(f"{UPLOADS_URL}{extracted_upload.id}/")

        assert response.status_code == 404

    def test_no_list_endpoint(self, auth_client):
        assert auth_client.get(UPLOADS_URL).status_code == 405

    def test_file_url_is_never_exposed(self, extracted_upload, auth_client):
        detail = auth_client.get(f"{UPLOADS_URL}{extracted_upload.id}/").data

        assert "file" not in detail


class TestEditExtractedExercise:
    def test_correct_statement(self, extracted_upload, auth_client):
        exercise = extracted_upload.exercises.first()

        response = auth_client.patch(exercise_url(exercise), {"statement": "  Résoudre $x^2 = 9$.  "}, format="json")

        assert response.status_code == 200
        exercise.refresh_from_db()
        assert exercise.statement == "Résoudre $x^2 = 9$."

    @pytest.mark.parametrize("statement, message", [("<b>gras</b>", "HTML"), ("   ", "vide"), ("x" * 5001, "trop long")])
    def test_invalid_statement(self, extracted_upload, auth_client, statement, message):
        exercise = extracted_upload.exercises.first()

        response = auth_client.patch(exercise_url(exercise), {"statement": statement}, format="json")

        assert response.status_code == 400
        assert message in str(response.data["statement"])

    def test_set_chapter(self, extracted_upload, auth_client, chapter):
        exercise = extracted_upload.exercises.first()

        response = auth_client.patch(exercise_url(exercise), {"chapter": str(chapter.id)}, format="json")

        assert response.status_code == 200
        assert response.data["chapter"] == chapter.id

    def test_chapter_must_match_subject_and_level(self, extracted_upload, auth_client, chapter):
        exercise = extracted_upload.exercises.first()

        response = auth_client.patch(
            exercise_url(exercise), {"chapter": str(chapter.id), "level": "Tle"}, format="json"
        )

        assert response.status_code == 400
        assert "chapter" in response.data

    def test_changing_subject_clears_chapter(self, extracted_upload, auth_client, chapter):
        exercise = extracted_upload.exercises.first()
        exercise.chapter = chapter
        exercise.save()

        response = auth_client.patch(exercise_url(exercise), {"subject": "svt"}, format="json")

        assert response.status_code == 200
        assert (response.data["subject"], response.data["chapter"]) == ("svt", None)

    def test_other_students_cannot_edit(self, extracted_upload, other_client):
        exercise = extracted_upload.exercises.first()
        response = other_client.patch(exercise_url(exercise), {"statement": "Piraté"}, format="json")

        assert response.status_code == 404

    def test_validated_statement_is_frozen(self, extracted_upload, auth_client):
        exercise = extracted_upload.exercises.first()
        auth_client.post(exercise_url(exercise, "validate/"))

        assert auth_client.patch(exercise_url(exercise), {"statement": "Modifié"}, format="json").status_code == 400
        assert auth_client.delete(exercise_url(exercise)).status_code == 400


class TestValidation:
    def test_validate_requires_subject(self, extracted_upload, auth_client):
        exercise = extracted_upload.exercises.first()
        exercise.subject = None
        exercise.save()

        response = auth_client.post(exercise_url(exercise, "validate/"))

        assert response.status_code == 400
        assert "subject" in response.data

    def test_file_kept_until_all_statements_validated(self, extracted_upload, auth_client):
        first, second = extracted_upload.exercises.all()

        response = auth_client.post(exercise_url(first, "validate/"))
        assert response.status_code == 200 and response.data["validated_at"]
        extracted_upload.refresh_from_db()
        assert extracted_upload.file

        auth_client.post(exercise_url(second, "validate/"))
        extracted_upload.refresh_from_db()
        assert not extracted_upload.file

    def test_validate_is_idempotent(self, extracted_upload, auth_client):
        exercise = extracted_upload.exercises.first()
        first = auth_client.post(exercise_url(exercise, "validate/")).data["validated_at"]
        second = auth_client.post(exercise_url(exercise, "validate/")).data["validated_at"]

        assert first == second

    def test_discarding_last_pending_statement_deletes_file(self, extracted_upload, auth_client):
        first, second = extracted_upload.exercises.all()
        auth_client.post(exercise_url(first, "validate/"))

        assert auth_client.delete(exercise_url(second)).status_code == 204
        extracted_upload.refresh_from_db()
        assert not extracted_upload.file


class TestPurge:
    def test_expired_files_are_deleted(self, extracted_upload, settings):
        settings.UPLOAD_FILE_RETENTION_HOURS = 48
        Upload.objects.update(created_at=timezone.now() - timedelta(hours=49))

        assert purge_expired_files() == 1
        extracted_upload.refresh_from_db()
        assert not extracted_upload.file
        assert extracted_upload.exercises.count() == 2

    def test_recent_files_are_kept(self, extracted_upload):
        assert purge_expired_files() == 0
