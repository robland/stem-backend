from datetime import timedelta
from io import StringIO

import pytest
from django.conf import settings as django_settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone

from config.celery import app as celery_app
from curriculum.models import Subject
from ingestion.models import Upload
from ingestion.services import ERROR_INTERRUPTED, recover_stuck_uploads
from learning.models import Exercise
from learning.services import recover_stuck_generations
from learning.tests.test_generation import make_extracted
from llm.tests.factories import generated_exercise

from .factories import extracted, extraction_response, image_bytes

pytestmark = pytest.mark.django_db


def make_upload(user, status, minutes_ago):
    upload = Upload(user=user, file_type="image", file_size=1, file_hash=f"h-{status}-{minutes_ago}", status=status)
    upload.file.save("document", ContentFile(image_bytes()), save=False)
    upload.save()
    Upload.objects.filter(id=upload.id).update(updated_at=timezone.now() - timedelta(minutes=minutes_ago))
    return upload


def make_exercise(user, status, minutes_ago):
    exercise = Exercise.objects.create(
        owner=user, source=make_extracted(user, file_hash=f"x-{status}-{minutes_ago}"),
        subject=Subject.objects.get(code="maths"),
        level="3e", generation_status=status,
    )
    Exercise.objects.filter(id=exercise.id).update(updated_at=timezone.now() - timedelta(minutes=minutes_ago))
    return exercise


class TestStuckUploads:
    def test_never_started_extraction_is_relaunched(self, user, fake_llm):
        upload = make_upload(user, Upload.Status.PENDING, minutes_ago=30)
        fake_llm.queue(extraction_response(extracted()))

        assert recover_stuck_uploads() == (1, 0)

        upload.refresh_from_db()
        assert upload.status == Upload.Status.EXTRACTED

    def test_interrupted_reading_goes_to_error(self, user, fake_llm):
        upload = make_upload(user, Upload.Status.READING, minutes_ago=30)

        assert recover_stuck_uploads() == (0, 1)

        upload.refresh_from_db()
        assert (upload.status, upload.error_message) == (Upload.Status.ERROR, ERROR_INTERRUPTED)
        assert not upload.file
        assert fake_llm.calls == []

    def test_recent_jobs_are_left_alone(self, user, fake_llm):
        make_upload(user, Upload.Status.PENDING, minutes_ago=5)
        make_upload(user, Upload.Status.READING, minutes_ago=5)

        assert recover_stuck_uploads() == (0, 0)
        assert fake_llm.calls == []

    def test_finished_uploads_are_ignored(self, user):
        make_upload(user, Upload.Status.EXTRACTED, minutes_ago=600)
        make_upload(user, Upload.Status.ERROR, minutes_ago=600)

        assert recover_stuck_uploads() == (0, 0)

    def test_threshold_is_configurable(self, user, fake_llm, settings):
        settings.JOB_STUCK_AFTER_MINUTES = 60
        make_upload(user, Upload.Status.READING, minutes_ago=30)

        assert recover_stuck_uploads() == (0, 0)


class TestStuckGenerations:
    def test_never_started_generation_is_relaunched(self, user, fake_llm):
        exercise = make_exercise(user, Exercise.GenerationStatus.PENDING, minutes_ago=30)
        fake_llm.queue(generated_exercise())

        assert recover_stuck_generations() == (1, 0)

        exercise.refresh_from_db()
        assert exercise.generation_status == Exercise.GenerationStatus.READY

    def test_interrupted_generation_can_be_relaunched_by_student(
        self, user, auth_client, fake_llm, settings, django_capture_on_commit_callbacks
    ):
        settings.GENERATION_DAILY_QUOTA = 1
        exercise = make_exercise(user, Exercise.GenerationStatus.GENERATING, minutes_ago=30)

        assert recover_stuck_generations() == (0, 1)
        exercise.refresh_from_db()
        assert exercise.generation_status == Exercise.GenerationStatus.ERROR
        assert "interrompue" in exercise.error_message

        fake_llm.queue(generated_exercise())
        with django_capture_on_commit_callbacks(execute=True):
            response = auth_client.post(f"/api/extracted-exercises/{exercise.source_id}/generate/")
        assert response.status_code == 202  # pas de quota consommé en plus
        exercise.refresh_from_db()
        assert exercise.generation_status == Exercise.GenerationStatus.READY

    def test_recent_generations_are_left_alone(self, user):
        make_exercise(user, Exercise.GenerationStatus.GENERATING, minutes_ago=5)

        assert recover_stuck_generations() == (0, 0)


class TestScheduling:
    def test_beat_schedule_targets_registered_tasks(self):
        celery_app.loader.import_default_modules()

        for entry in django_settings.CELERY_BEAT_SCHEDULE.values():
            assert entry["task"] in celery_app.tasks

    def test_stuck_threshold_exceeds_task_time_limit(self):
        assert django_settings.JOB_STUCK_AFTER_MINUTES * 60 > django_settings.CELERY_TASK_TIME_LIMIT

    def test_maintenance_task(self, user):
        make_upload(user, Upload.Status.READING, minutes_ago=30)

        result = celery_app.tasks["ingestion.tasks.run_maintenance"].delay().get()

        assert result == {"uploads": (0, 1), "generations": (0, 0)}

    def test_maintenance_command(self, user, settings):
        make_upload(user, Upload.Status.READING, minutes_ago=30)
        settings.UPLOAD_FILE_RETENTION_HOURS = 48
        expired = make_upload(user, Upload.Status.EXTRACTED, minutes_ago=0)
        Upload.objects.filter(id=expired.id).update(created_at=timezone.now() - timedelta(hours=49))
        out = StringIO()

        call_command("run_maintenance", stdout=out)

        assert "Uploads : 0 relancé(s), 1 mis en erreur." in out.getvalue()
        assert "Fichiers expirés supprimés : 1." in out.getvalue()
