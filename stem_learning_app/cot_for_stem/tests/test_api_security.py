from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from cot_for_stem.models import Document, Subject, Chapter, Exercise, Step, QCM

pytestmark = pytest.mark.django_db


@pytest.fixture
def subject():
    return Subject.objects.create(name="Maths")


@pytest.fixture
def exercise(subject, user):
    chapter = Chapter.objects.create(name="Fonctions", subject=subject)
    document = Document.objects.create(
        user=user, file="documents/x.jpg", file_type="image",
        original_filename="x.jpg", file_size=1, file_hash="h1",
    )
    return Exercise.objects.create(
        document=document, chapter=chapter, statement="Énoncé",
        formula=[], intuition={}, concepts_used=[], raw_text={},
    )


@pytest.fixture
def mock_pipeline():
    with mock.patch("cot_for_stem.views.process_document_pipeline") as pipeline:
        yield pipeline


def image(content=b"fake-image"):
    return SimpleUploadedFile("exo.jpg", content, content_type="image/jpeg")


class TestAuthenticationRequired:
    @pytest.mark.parametrize("url", [
        "/api/stem/subjects/",
        "/api/stem/chapters/",
        "/api/stem/all-exercises/",
        "/api/stem/exercises/",
    ])
    def test_anonymous_cannot_read(self, api_client, url):
        assert api_client.get(url).status_code == 401

    def test_anonymous_cannot_upload(self, api_client, mock_pipeline):
        response = api_client.post(reverse("upload_document"), {"file": image()}, format="multipart")

        assert response.status_code == 401
        mock_pipeline.delay.assert_not_called()

    def test_authenticated_can_read(self, auth_client, subject):
        response = auth_client.get("/api/stem/subjects/")

        assert response.status_code == 200
        assert response.data[0]["name"] == "Maths"


class TestReadOnlyCatalogue:
    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_students_cannot_modify_subjects(self, auth_client, subject, method):
        url = "/api/stem/subjects/" if method == "post" else f"/api/stem/subjects/{subject.id}/"

        response = getattr(auth_client, method)(url, {"name": "Piraté"}, format="json")

        assert response.status_code == 405
        assert Subject.objects.get().name == "Maths"

    def test_students_cannot_delete_exercises(self, auth_client, exercise):
        response = auth_client.delete(f"/api/stem/all-exercises/{exercise.id}/")

        assert response.status_code == 405
        assert Exercise.objects.filter(id=exercise.id).exists()


class TestUpload:
    def test_links_document_to_user_and_starts_pipeline(self, auth_client, user, mock_pipeline):
        response = auth_client.post(reverse("upload_document"), {"file": image()}, format="multipart")

        assert response.status_code == 201
        document = Document.objects.get(id=response.data["document_id"])
        assert document.user == user
        mock_pipeline.delay.assert_called_once_with(str(document.id))

    def test_same_file_is_not_processed_twice(self, auth_client, mock_pipeline):
        auth_client.post(reverse("upload_document"), {"file": image()}, format="multipart")

        response = auth_client.post(reverse("upload_document"), {"file": image()}, format="multipart")

        assert response.status_code == 200
        assert response.data["status"] == "already_processed"
        assert mock_pipeline.delay.call_count == 1

    def test_missing_file_is_rejected(self, auth_client, mock_pipeline):
        response = auth_client.post(reverse("upload_document"), {}, format="multipart")

        assert response.status_code == 400
        mock_pipeline.delay.assert_not_called()


class TestExercises:
    def test_filter_by_document(self, auth_client, exercise):
        other = Document.objects.create(
            file="documents/y.jpg", file_type="image", original_filename="y.jpg", file_size=1, file_hash="h2",
        )

        matching = auth_client.get(reverse("exercises"), {"id": exercise.document.id})
        empty = auth_client.get(reverse("exercises"), {"id": other.id})

        assert [e["id"] for e in matching.data] == [str(exercise.id)]
        assert empty.data == []

    def test_solved_state_is_computed_for_current_user(self, auth_client, exercise):
        response = auth_client.get(reverse("exercises"))

        assert response.data[0]["solved"] == {"state": "not_started", "score": 0}

    def test_qcm_never_exposes_correct_choice(self, auth_client, exercise):
        step = Step.objects.create(exercise=exercise, step_number=1, objective="Dériver")
        QCM.objects.create(step=step, question="f'(x) ?", correct_choice="A")

        response = auth_client.get(reverse("qcm", args=[step.id]))

        assert response.status_code == 200
        assert "correct_choice" not in response.data[0]


class TestReprocessDocument:
    def test_student_cannot_trigger(self, auth_client, exercise, mock_pipeline):
        response = auth_client.post(reverse("process_document", args=[exercise.document.id]))

        assert response.status_code == 403
        mock_pipeline.delay.assert_not_called()

    def test_admin_can_trigger(self, admin_client, exercise, mock_pipeline):
        response = admin_client.post(reverse("process_document", args=[exercise.document.id]))

        assert response.status_code == 202
        mock_pipeline.delay.assert_called_once_with(str(exercise.document.id))
