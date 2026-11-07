import pytest

from ingestion.tests.test_events import parse
from learning.models import Exercise

from .test_exercises_api import make_exercise

pytestmark = pytest.mark.django_db

Status = Exercise.GenerationStatus


def open_stream(client, exercise):
    return client.get(f"/api/exercises/{exercise.id}/events/", HTTP_ACCEPT="text/event-stream")


def test_streams_generation_until_ready_with_public_content(auth_client, user):
    exercise = make_exercise(user, status=Status.PENDING)
    chunks = iter(open_stream(auth_client, exercise).streaming_content)
    next(chunks)
    name, data = parse(next(chunks))
    assert (name, data["content"]) == ("pending", None)

    Exercise.objects.filter(pk=exercise.pk).update(generation_status=Status.GENERATING)
    assert parse(next(chunks))[0] == "generating"

    Exercise.objects.filter(pk=exercise.pk).update(generation_status=Status.READY)
    name, data = parse(next(chunks))
    assert name == "ready"
    assert data["content"]["steps"][0]["id"] == "s1"
    # Contenu public : jamais la réponse attendue dans le flux.
    assert "answer" not in data["content"]["steps"][0]["activity"]
    assert list(chunks) == []


@pytest.mark.parametrize("status", [Status.NEEDS_REVIEW, Status.ERROR])
def test_failed_generation_ends_the_stream_without_content(auth_client, user, status):
    chunks = list(open_stream(auth_client, make_exercise(user, status=status)).streaming_content)

    name, data = parse(chunks[-1])
    assert (len(chunks), name, data["content"]) == (2, status, None)


def test_other_students_cannot_follow(other_client, user):
    assert open_stream(other_client, make_exercise(user, status=Status.PENDING)).status_code == 404
