import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from challenges.models import Challenge
from conftest import PASSWORD, _client_for
from learning.models import Attempt, Exercise
from learning.tests.test_attempts import RIGHT, WRONG, make_exercise

pytestmark = pytest.mark.django_db

URL = "/api/challenges/"
ACCEPTABLE = {"acceptable": True, "reasons": []}


def student(pseudo, phone):
    user = User.objects.create_user(phone=phone, pseudo=pseudo, password=PASSWORD, level="3e")
    return user, _client_for(user)


def finish(user, exercise):
    """L'auteur a travaillé son parcours (condition pour le partager)."""
    now = timezone.now()
    Attempt.objects.create(user=user, exercise=exercise, started_at=now, finished_at=now, score=100)


@pytest.fixture
def exercise(user):
    exercise = make_exercise(user)
    finish(user, exercise)
    return exercise


def create(client, exercise, captured=None, **data):
    payload = {"exercise": str(exercise.id), "visibility": "private"} | data
    if captured is None:
        return client.post(URL, payload, format="json")
    with captured(execute=True):
        return client.post(URL, payload, format="json")


@pytest.fixture
def private(auth_client, exercise):
    response = create(auth_client, exercise)
    assert response.status_code == 201, response.data
    return Challenge.objects.get(id=response.data["id"])


def join(client, challenge, **data):
    return client.post(f"{URL}{challenge.id}/attempts/", data, format="json")


def play(client, attempt_id, answers, tries=1):
    """Répond à chaque étape ; `tries` = 3 avec des réponses fausses fait échouer chaque étape."""
    for step_id in ("s1", "s2"):
        for _ in range(tries):
            response = client.post(
                f"/api/attempts/{attempt_id}/answers/",
                {"step_id": step_id, "response": answers[step_id], "client_uuid": str(uuid.uuid4())},
                format="json",
            )
            assert response.status_code == 201, response.data


class TestCreate:
    def test_private_challenge_is_active_with_a_code(self, auth_client, exercise):
        response = create(auth_client, exercise, timed=True, hints_allowed=False)

        assert response.status_code == 201
        data = response.data
        assert (data["status"], data["visibility"], data["timed"], data["hints_allowed"]) == (
            "active", "private", True, False,
        )
        assert len(data["code"]) == 6 and data["is_author"] and data["author"] == "eleve"
        assert data["content"]["statement"] == exercise.content["statement"]

    def test_exercise_must_be_finished_once(self, auth_client, user):
        response = create(auth_client, make_exercise(user))

        assert response.status_code == 400
        assert "Termine" in response.data["detail"]

    def test_exercise_must_be_ready(self, auth_client, user):
        exercise = make_exercise(user, status=Exercise.GenerationStatus.NEEDS_REVIEW)
        finish(user, exercise)

        assert create(auth_client, exercise).status_code == 400

    def test_only_own_exercise(self, other_client, exercise):
        assert create(other_client, exercise).status_code == 400

    def test_requires_authentication(self, api_client):
        assert api_client.get(URL).status_code == 401


class TestModeration:
    def test_public_challenge_is_checked_then_listed(
        self, auth_client, other_client, exercise, fake_llm, django_capture_on_commit_callbacks
    ):
        fake_llm.queue(ACCEPTABLE)

        response = create(auth_client, exercise, django_capture_on_commit_callbacks, visibility="public")

        assert response.data["status"] == "pending"
        assert fake_llm.calls[0]["prompt"].id == "moderation.v1"
        assert exercise.content["statement"] in fake_llm.calls[0]["prompt"].user
        challenge = Challenge.objects.get(id=response.data["id"])
        assert (challenge.status, challenge.moderation_prompt_id) == ("active", "moderation.v1")
        catalogue = other_client.get(URL).data["results"]
        assert [c["id"] for c in catalogue] == [str(challenge.id)]
        assert catalogue[0]["code"] is None  # le code n'est montré qu'à l'auteur

    def test_rejected_statement_is_explained_to_the_author_only(
        self, auth_client, other_client, exercise, fake_llm, django_capture_on_commit_callbacks
    ):
        fake_llm.queue({"acceptable": False, "reasons": ["personal_data"]})

        response = create(auth_client, exercise, django_capture_on_commit_callbacks, visibility="public")

        mine = auth_client.get(URL, {"scope": "mine"}).data["results"][0]
        assert mine["status"] == "rejected"
        assert "informations personnelles" in mine["moderation_messages"][0]
        assert other_client.get(URL).data["results"] == []
        assert other_client.get(f"{URL}{response.data['id']}/").status_code == 404

    def test_llm_failure_leaves_it_pending_until_maintenance(
        self, auth_client, exercise, fake_llm, django_capture_on_commit_callbacks, settings
    ):
        from challenges.services import recover_pending_moderations
        from llm.exceptions import LLMError

        fake_llm.queue(LLMError("réseau"))
        response = create(auth_client, exercise, django_capture_on_commit_callbacks, visibility="public")
        challenge = Challenge.objects.get(id=response.data["id"])
        assert challenge.status == "pending"

        Challenge.objects.filter(id=challenge.id).update(updated_at=timezone.now() - timedelta(hours=1))
        fake_llm.queue(ACCEPTABLE)
        assert recover_pending_moderations() == 1

        challenge.refresh_from_db()
        assert challenge.status == "active"

    def test_same_statement_is_not_listed_twice(
        self, auth_client, other_user, other_client, exercise, fake_llm, django_capture_on_commit_callbacks
    ):
        Exercise.objects.filter(id=exercise.id).update(content_hash="abc")
        fake_llm.queue(ACCEPTABLE)
        create(auth_client, exercise, django_capture_on_commit_callbacks, visibility="public")
        copy = make_exercise(other_user)
        Exercise.objects.filter(id=copy.id).update(content_hash="abc")
        finish(other_user, copy)

        response = create(other_client, copy, visibility="public")

        assert response.status_code == 400
        assert "catalogue" in response.data["detail"]
        assert create(other_client, copy).status_code == 201  # en privé, c'est permis


class TestCatalogue:
    def test_filters(self, auth_client, other_client, exercise, fake_llm, django_capture_on_commit_callbacks):
        fake_llm.queue(ACCEPTABLE)
        create(auth_client, exercise, django_capture_on_commit_callbacks, visibility="public")

        assert len(other_client.get(URL, {"subject": "maths", "level": "3e"}).data["results"]) == 1
        assert other_client.get(URL, {"level": "Tle"}).data["results"] == []
        assert other_client.get(URL, {"scope": "nope"}).status_code == 400

    def test_private_challenges_are_not_in_the_catalogue(self, other_client, private):
        assert other_client.get(URL).data["results"] == []
        assert other_client.get(f"{URL}{private.id}/").status_code == 404

    def test_find_by_code(self, other_client, private):
        response = other_client.get(f"{URL}code/{private.code.lower()}/")

        assert response.status_code == 200
        assert response.data["id"] == str(private.id) and response.data["code"] is None
        assert "answer" not in response.data["content"]["steps"][0]["activity"]
        assert other_client.get(f"{URL}code/ZZZZZZ/").status_code == 404


class TestPlay:
    def test_private_challenge_needs_its_code(self, other_client, private):
        assert join(other_client, private).status_code == 400

        response = join(other_client, private, code=private.code)

        assert response.status_code == 201
        assert (response.data["mode"], str(response.data["challenge"])) == ("challenge", str(private.id))

    def test_one_attempt_per_student(self, other_client, private):
        first = join(other_client, private, code=private.code)
        again = join(other_client, private, code=private.code)

        assert (first.status_code, again.status_code) == (201, 200)
        assert first.data["id"] == again.data["id"]
        detail = other_client.get(f"{URL}{private.id}/").data
        assert detail["my_attempt"] == first.data["id"]
        assert other_client.get(URL, {"scope": "joined"}).data["results"][0]["id"] == str(private.id)

    def test_author_cannot_play_own_challenge(self, auth_client, private):
        assert join(auth_client, private, code=private.code).status_code == 400

    def test_hidden_challenge_cannot_be_started(self, other_client, private):
        Challenge.objects.filter(id=private.id).update(status=Challenge.Status.HIDDEN)

        assert join(other_client, private, code=private.code).status_code == 400

    def test_answers_are_graded_online(self, other_client, private):
        attempt_id = join(other_client, private, code=private.code).data["id"]

        play(other_client, attempt_id, RIGHT)

        assert other_client.get(f"/api/attempts/{attempt_id}/").data["score"] == 100

    def test_hints_can_be_disabled(self, auth_client, other_client, exercise):
        challenge = Challenge.objects.get(id=create(auth_client, exercise, hints_allowed=False).data["id"])
        attempt_id = join(other_client, challenge, code=challenge.code).data["id"]

        response = other_client.post(f"/api/attempts/{attempt_id}/hints/", {"step_id": "s1"}, format="json")

        assert response.status_code == 400
        content = other_client.get(f"{URL}{challenge.id}/").data["content"]
        assert all(step["hints"] == [] for step in content["steps"])

    def test_offline_hints_do_not_count_in_a_challenge(self, other_client, private):
        attempt_id = join(other_client, private, code=private.code).data["id"]

        other_client.post(
            f"/api/attempts/{attempt_id}/answers/",
            {"step_id": "s1", "response": RIGHT["s1"], "client_uuid": str(uuid.uuid4()), "hints_used": 3},
            format="json",
        )

        assert other_client.get(f"/api/attempts/{attempt_id}/").data["hints_used"] == 0

    def test_challenge_attempts_cannot_be_synced(self, other_client, private):
        attempt_id = join(other_client, private, code=private.code).data["id"]
        payload = {"attempts": [{
            "id": attempt_id, "exercise": str(private.exercise_id), "started_at": timezone.now().isoformat(),
            "answers": [],
        }]}

        response = other_client.post("/api/sync/", payload, format="json")

        assert response.data["attempts"][0]["status"] == "rejected"


class TestReports:
    def test_hidden_after_three_reports(self, private, settings):
        for i in range(3):
            user, client = student(f"témoin{i}", f"+24206000000{i}")
            join(client, private, code=private.code)
            response = client.post(f"{URL}{private.id}/report/", {"reason": "inappropriate"}, format="json")
            assert response.status_code == 201
            # Renvoyer le même signalement ne compte pas deux fois.
            assert client.post(f"{URL}{private.id}/report/", {"reason": "other"}, format="json").status_code == 200

        private.refresh_from_db()
        assert private.status == "hidden"

    def test_author_cannot_report(self, auth_client, private):
        response = auth_client.post(f"{URL}{private.id}/report/", {"reason": "other"}, format="json")

        assert response.status_code == 400


class TestLeaderboard:
    def test_ranked_by_score_then_duration(self, auth_client, private):
        players = [student(name, f"+24206111111{i}") for i, name in enumerate(["lent", "rapide", "faible"])]
        attempts = {}
        for (user, client), answers in zip(players, [RIGHT, RIGHT, WRONG]):
            attempts[user.pseudo] = join(client, private, code=private.code).data["id"]
            play(client, attempts[user.pseudo], answers, tries=3 if answers is WRONG else 1)
        Attempt.objects.filter(id=attempts["lent"]).update(started_at=timezone.now() - timedelta(minutes=30))
        Attempt.objects.filter(id=attempts["rapide"]).update(started_at=timezone.now() - timedelta(minutes=5))

        board = players[2][1].get(f"{URL}{private.id}/leaderboard/").data

        assert [(e["rank"], e["pseudo"], e["score"]) for e in board["entries"]] == [
            (1, "rapide", 100), (2, "lent", 100), (3, "faible", 0),
        ]
        assert board["me"]["pseudo"] == "faible" and board["me"]["is_me"]
        assert (board["participants"], board["finished"]) == (3, 3)

        mine = auth_client.get(URL, {"scope": "mine"}).data["results"][0]
        assert (mine["finished"], mine["author_points"]) == (3, 30)
        assert auth_client.get("/api/progress/").data["summary"]["author_points"] == 30

    def test_author_points_are_capped(self, settings):
        from challenges.services import points_for

        assert [points_for(n) for n in (0, 1, 5, 12)] == [0, 10, 50, 50]

    def test_private_leaderboard_is_hidden_from_strangers(self, other_client, private):
        assert other_client.get(f"{URL}{private.id}/leaderboard/").status_code == 404
