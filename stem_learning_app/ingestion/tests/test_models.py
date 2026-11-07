import pytest
from django.db import IntegrityError

from ingestion.models import Upload, ExtractedExercise

pytestmark = pytest.mark.django_db


def make_upload(user, file_hash="abc"):
    return Upload.objects.create(user=user, file_type="image", file_size=10, file_hash=file_hash)


class TestUpload:
    def test_starts_pending(self, user):
        assert make_upload(user).status == Upload.Status.PENDING

    def test_same_file_allowed_for_two_students(self, user, other_user):
        make_upload(user)
        make_upload(other_user)

        assert Upload.objects.count() == 2

    def test_same_file_twice_for_one_student_is_rejected(self, user):
        make_upload(user)

        with pytest.raises(IntegrityError):
            make_upload(user)


class TestExtractedExercise:
    def test_order_is_unique_within_upload(self, user):
        upload = make_upload(user)
        ExtractedExercise.objects.create(upload=upload, order=0, statement="Exercice 1")

        with pytest.raises(IntegrityError):
            ExtractedExercise.objects.create(upload=upload, order=0, statement="Doublon")

    def test_deleting_upload_deletes_its_exercises(self, user):
        upload = make_upload(user)
        ExtractedExercise.objects.create(upload=upload, order=0, statement="Exercice 1")

        upload.delete()

        assert not ExtractedExercise.objects.exists()
