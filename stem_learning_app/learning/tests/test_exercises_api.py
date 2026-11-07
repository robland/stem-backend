import pytest

from curriculum.models import Subject
from learning.models import Exercise
from llm.schemas import SCHEMA_VERSION
from llm.tests.factories import generated_exercise, step

pytestmark = pytest.mark.django_db

URL = "/api/exercises/"


def make_exercise(owner, status=Exercise.GenerationStatus.READY, level="3e"):
    content = {"schema_version": SCHEMA_VERSION, "statement": "Énoncé", **generated_exercise(step("s1", "mcq"))}
    return Exercise.objects.create(
        owner=owner, subject=Subject.objects.get(code="maths"), level=level, title=content["title"],
        content=content, schema_version=SCHEMA_VERSION, generation_status=status,
    )


def test_requires_authentication(api_client):
    assert api_client.get(URL).status_code == 401


def test_list_only_own_exercises(auth_client, user, other_user):
    mine = make_exercise(user)
    make_exercise(other_user)

    response = auth_client.get(URL)

    assert response.status_code == 200
    assert [e["id"] for e in response.data["results"]] == [str(mine.id)]
    assert "content" not in response.data["results"][0]


def test_list_is_paginated(auth_client, user):
    for _ in range(21):
        make_exercise(user)

    response = auth_client.get(URL)

    assert len(response.data["results"]) == 20
    assert response.data["next"]


def test_detail_hides_answers(auth_client, user):
    exercise = make_exercise(user)

    data = auth_client.get(f"{URL}{exercise.id}/").data

    assert (data["subject"], data["exam"], data["schema_version"]) == ("maths", "BEPC", "1.1")
    activity = data["content"]["steps"][0]["activity"]
    assert activity["options"] and "answer" not in activity
    assert "explanation" not in data["content"]["steps"][0]


def test_detail_of_lycee_exercise_targets_bac(auth_client, user):
    exercise = make_exercise(user, level="Tle")

    assert auth_client.get(f"{URL}{exercise.id}/").data["exam"] == "BAC"


def test_content_is_null_until_ready(auth_client, user):
    exercise = make_exercise(user, status=Exercise.GenerationStatus.GENERATING)

    assert auth_client.get(f"{URL}{exercise.id}/").data["content"] is None
    assert auth_client.get(f"{URL}{exercise.id}/offline/").data["content"] is None


def test_offline_includes_answers_for_owner(auth_client, user):
    exercise = make_exercise(user)

    data = auth_client.get(f"{URL}{exercise.id}/offline/").data

    assert data["content"]["steps"][0]["activity"]["answer"] == {"option_ids": ["b"]}
    assert len(data["content"]["steps"][0]["hints"]) == 3


@pytest.mark.parametrize("suffix", ["", "offline/"])
def test_other_students_cannot_read(other_client, user, suffix):
    exercise = make_exercise(user)

    assert other_client.get(f"{URL}{exercise.id}/{suffix}").status_code == 404


def test_read_only(auth_client, user):
    exercise = make_exercise(user)

    assert auth_client.post(URL, {}).status_code == 405
    assert auth_client.delete(f"{URL}{exercise.id}/").status_code == 405
