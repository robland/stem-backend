import uuid

import pytest
from django.db import IntegrityError
from django.utils import timezone

from curriculum.models import Subject, Chapter
from learning.models import Exercise, Attempt, StepAnswer, Mastery

pytestmark = pytest.mark.django_db


@pytest.fixture
def chapter():
    return Chapter.objects.create(subject=Subject.objects.get(code="maths"), level="3e", name="Fonctions affines")


@pytest.fixture
def exercise(user, chapter):
    return Exercise.objects.create(owner=user, subject=chapter.subject, chapter=chapter, level="3e")


@pytest.fixture
def attempt(user, exercise):
    return Attempt.objects.create(user=user, exercise=exercise, started_at=timezone.now())


def answer(attempt, client_uuid):
    return StepAnswer.objects.create(
        attempt=attempt, step_id="s1", response={"option_ids": ["b"]}, is_correct=True,
        answered_at=timezone.now(), client_uuid=client_uuid,
    )


class TestExercise:
    def test_defaults(self, exercise):
        assert exercise.generation_status == Exercise.GenerationStatus.PENDING
        assert exercise.content == {}

    def test_subject_cannot_be_deleted_while_used(self, exercise):
        with pytest.raises(IntegrityError):
            Subject.objects.filter(code="maths").delete()


class TestStepAnswer:
    def test_client_uuid_makes_sync_idempotent(self, attempt):
        client_uuid = uuid.uuid4()
        answer(attempt, client_uuid)

        with pytest.raises(IntegrityError):
            answer(attempt, client_uuid)


class TestMastery:
    def test_one_mastery_per_user_and_chapter(self, user, chapter):
        Mastery.objects.create(user=user, chapter=chapter)

        with pytest.raises(IntegrityError):
            Mastery.objects.create(user=user, chapter=chapter)

    def test_score_cannot_exceed_100(self, user, chapter):
        with pytest.raises(IntegrityError):
            Mastery.objects.create(user=user, chapter=chapter, score=101)
