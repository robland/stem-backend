import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from curriculum.models import Subject
from learning.models import Attempt, Exercise, StepAnswer
from llm.schemas import SCHEMA_VERSION
from llm.tests.factories import generated_exercise, step

pytestmark = pytest.mark.django_db

RIGHT = {"s1": {"option_ids": ["b"]}, "s2": {"coefficients": [2, 1, 2]}}
WRONG = {"s1": {"option_ids": ["a"]}, "s2": {"coefficients": [1, 1, 1]}}


def make_exercise(owner, status=Exercise.GenerationStatus.READY):
    content = {
        "schema_version": SCHEMA_VERSION,
        "statement": "Énoncé",
        **generated_exercise(step("s1", "mcq"), step("s2", "chem_balance")),
    }
    return Exercise.objects.create(
        owner=owner, subject=Subject.objects.get(code="maths"), level="3e", title=content["title"],
        content=content, schema_version=SCHEMA_VERSION, generation_status=status,
    )


@pytest.fixture
def exercise(user):
    return make_exercise(user)


@pytest.fixture
def attempt(auth_client, exercise):
    response = auth_client.post(f"/api/exercises/{exercise.id}/attempts/", {}, format="json")
    assert response.status_code == 201
    return Attempt.objects.get(id=response.data["id"])


def answer(client, attempt, step_id, response, **extra):
    payload = {"step_id": step_id, "response": response, "client_uuid": str(uuid.uuid4())} | extra
    return client.post(f"/api/attempts/{attempt.id}/answers/", payload, format="json")


def hint(client, attempt, step_id):
    return client.post(f"/api/attempts/{attempt.id}/hints/", {"step_id": step_id}, format="json")


class TestStart:
    def test_start(self, attempt, auth_client):
        data = auth_client.get(f"/api/attempts/{attempt.id}/").data

        assert (data["score"], data["finished_at"], data["current_step_id"]) == (0, None, "s1")
        assert [s["status"] for s in data["steps"]] == ["pending", "pending"]

    def test_client_id_makes_start_idempotent(self, auth_client, exercise):
        attempt_id = str(uuid.uuid4())
        url = f"/api/exercises/{exercise.id}/attempts/"

        first = auth_client.post(url, {"id": attempt_id}, format="json")
        second = auth_client.post(url, {"id": attempt_id}, format="json")

        assert (first.status_code, second.status_code) == (201, 200)
        assert Attempt.objects.count() == 1

    def test_id_of_another_student_is_refused(self, auth_client, other_client, other_user, exercise):
        other_exercise = make_exercise(other_user)
        attempt_id = str(uuid.uuid4())
        other_client.post(f"/api/exercises/{other_exercise.id}/attempts/", {"id": attempt_id}, format="json")

        response = auth_client.post(f"/api/exercises/{exercise.id}/attempts/", {"id": attempt_id}, format="json")

        assert response.status_code == 400

    def test_exercise_not_ready(self, auth_client, user):
        exercise = make_exercise(user, status=Exercise.GenerationStatus.NEEDS_REVIEW)

        response = auth_client.post(f"/api/exercises/{exercise.id}/attempts/", {}, format="json")

        assert response.status_code == 400
        assert "pas encore prêt" in response.data["detail"]

    def test_other_students_exercise(self, other_client, exercise):
        assert other_client.post(f"/api/exercises/{exercise.id}/attempts/", {}, format="json").status_code == 404

    def test_other_students_attempt_is_hidden(self, other_client, attempt):
        assert other_client.get(f"/api/attempts/{attempt.id}/").status_code == 404
        assert answer(other_client, attempt, "s1", RIGHT["s1"]).status_code == 404


class TestAnswers:
    def test_correct_answer_closes_step(self, auth_client, attempt):
        response = answer(auth_client, attempt, "s1", RIGHT["s1"])

        assert response.status_code == 201
        assert response.data["is_correct"] is True
        assert response.data["step"] == {
            "step_id": "s1", "status": "succeeded", "wrong_answers": 0, "hints_used": 0, "score": 100,
        }
        assert response.data["explanation"]
        assert response.data["attempt"]["current_step_id"] == "s2"
        assert response.data["attempt"]["score"] == 50

    def test_wrong_answer_gives_feedback_but_not_the_correction(self, auth_client, attempt):
        response = answer(auth_client, attempt, "s2", WRONG["s2"])

        assert response.status_code == 400  # s2 n'est pas l'étape en cours

        response = answer(auth_client, attempt, "s1", WRONG["s1"])

        assert response.data["is_correct"] is False
        assert response.data["feedback"]
        assert response.data["explanation"] is None
        assert response.data["step"]["status"] == "pending"

    def test_step_fails_after_max_wrong_answers(self, auth_client, attempt, settings):
        settings.ATTEMPT_MAX_WRONG_ANSWERS = 3
        for _ in range(2):
            answer(auth_client, attempt, "s1", WRONG["s1"])

        response = answer(auth_client, attempt, "s1", WRONG["s1"])

        assert response.data["step"]["status"] == "failed"
        assert response.data["explanation"]
        assert response.data["attempt"]["current_step_id"] == "s2"

    def test_full_attempt_score(self, auth_client, attempt):
        hint(auth_client, attempt, "s1")
        answer(auth_client, attempt, "s1", WRONG["s1"])
        answer(auth_client, attempt, "s1", RIGHT["s1"])  # 100 − 20 (indice) − 20 (erreur) = 60

        response = answer(auth_client, attempt, "s2", RIGHT["s2"])  # 100

        data = response.data["attempt"]
        assert data["score"] == 80
        assert data["hints_used"] == 1
        assert data["finished_at"] and data["current_step_id"] is None

    def test_finished_attempt_refuses_answers(self, auth_client, attempt):
        answer(auth_client, attempt, "s1", RIGHT["s1"])
        answer(auth_client, attempt, "s2", RIGHT["s2"])

        response = answer(auth_client, attempt, "s2", RIGHT["s2"])

        assert response.status_code == 400
        assert "terminée" in response.data["detail"]

    def test_same_client_uuid_is_idempotent(self, auth_client, attempt):
        client_uuid = str(uuid.uuid4())
        first = answer(auth_client, attempt, "s1", WRONG["s1"], client_uuid=client_uuid)
        second = answer(auth_client, attempt, "s1", WRONG["s1"], client_uuid=client_uuid)

        assert (first.status_code, second.status_code) == (201, 200)
        assert second.data["is_correct"] is False
        assert StepAnswer.objects.count() == 1

    def test_client_uuid_of_another_attempt_is_refused(self, auth_client, attempt, exercise):
        client_uuid = str(uuid.uuid4())
        answer(auth_client, attempt, "s1", WRONG["s1"], client_uuid=client_uuid)
        other = auth_client.post(f"/api/exercises/{exercise.id}/attempts/", {}, format="json").data

        response = auth_client.post(
            f"/api/attempts/{other['id']}/answers/",
            {"step_id": "s1", "response": WRONG["s1"], "client_uuid": client_uuid},
            format="json",
        )

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "payload, field",
        [
            ({"step_id": "s1", "response": [1], "client_uuid": str(uuid.uuid4())}, "response"),
            ({"step_id": "s1", "response": {}, "client_uuid": "pas-un-uuid"}, "client_uuid"),
            ({"step_id": "s1", "response": {}, "client_uuid": str(uuid.uuid4()), "hints_used": 9}, "hints_used"),
        ],
    )
    def test_invalid_payload(self, auth_client, attempt, payload, field):
        response = auth_client.post(f"/api/attempts/{attempt.id}/answers/", payload, format="json")

        assert response.status_code == 400
        assert field in response.data

    def test_malformed_response_for_activity(self, auth_client, attempt):
        response = answer(auth_client, attempt, "s1", {"value": True})

        assert response.status_code == 400
        assert "mcq" in response.data["detail"]
        assert not StepAnswer.objects.exists()

    def test_unknown_step(self, auth_client, attempt):
        assert answer(auth_client, attempt, "s9", {}).status_code == 400

    def test_future_answer_time_is_clamped(self, auth_client, attempt):
        answer(auth_client, attempt, "s1", RIGHT["s1"], answered_at=(timezone.now() + timedelta(days=1)).isoformat())

        assert StepAnswer.objects.get().answered_at <= timezone.now()


class TestHints:
    def test_hints_are_given_in_order_and_counted(self, auth_client, attempt):
        first = hint(auth_client, attempt, "s1")
        second = hint(auth_client, attempt, "s1")
        third = hint(auth_client, attempt, "s1")

        content = attempt.exercise.content["steps"][0]["hints"]
        assert [r.data["hint"] for r in (first, second, third)] == content
        assert [r.data["level"] for r in (first, second, third)] == [1, 2, 3]
        assert hint(auth_client, attempt, "s1").status_code == 400

        data = auth_client.get(f"/api/attempts/{attempt.id}/").data
        assert data["hints_used"] == 3
        assert data["steps"][0]["hints_used"] == 3

    def test_hint_only_for_current_step(self, auth_client, attempt):
        assert hint(auth_client, attempt, "s2").status_code == 400

    def test_hints_reduce_step_score_to_zero_at_most(self, auth_client, attempt):
        for _ in range(3):
            hint(auth_client, attempt, "s1")
        answer(auth_client, attempt, "s1", WRONG["s1"])
        answer(auth_client, attempt, "s1", WRONG["s1"])

        response = answer(auth_client, attempt, "s1", RIGHT["s1"])

        assert response.data["step"]["score"] == 0


class TestSync:
    def payload(self, exercise, answers, attempt_id=None, started_at=None):
        now = timezone.now()
        return {
            "attempts": [{
                "id": attempt_id or str(uuid.uuid4()),
                "exercise": str(exercise.id),
                "started_at": (started_at or now - timedelta(hours=2)).isoformat(),
                "answers": answers,
            }]
        }

    def offline_answer(self, step_id, response, minutes_ago, hints_used=0):
        return {
            "client_uuid": str(uuid.uuid4()), "step_id": step_id, "response": response,
            "answered_at": (timezone.now() - timedelta(minutes=minutes_ago)).isoformat(), "hints_used": hints_used,
        }

    def test_offline_attempt_is_replayed_and_regraded(self, auth_client, exercise):
        answers = [
            # Envoyées dans le désordre : rejouées par answered_at.
            self.offline_answer("s2", RIGHT["s2"], minutes_ago=10),
            self.offline_answer("s1", RIGHT["s1"], minutes_ago=30, hints_used=2),
        ]

        response = auth_client.post("/api/sync/", self.payload(exercise, answers), format="json")

        assert response.status_code == 200
        [result] = response.data["attempts"]
        assert result["status"] == "synced"
        assert sorted(a["status"] for a in result["answers"]) == ["accepted", "accepted"]
        assert result["attempt"]["score"] == 80  # s1 : 100 − 2×20 ; s2 : 100
        assert result["attempt"]["finished_at"]
        attempt = Attempt.objects.get()
        assert attempt.hints == {"s1": 2}
        assert attempt.started_at < timezone.now() - timedelta(hours=1)

    def test_resync_is_idempotent(self, auth_client, exercise):
        payload = self.payload(exercise, [self.offline_answer("s1", WRONG["s1"], minutes_ago=5)])

        auth_client.post("/api/sync/", payload, format="json")
        response = auth_client.post("/api/sync/", payload, format="json")

        assert response.data["attempts"][0]["answers"][0]["status"] == "duplicate"
        assert (Attempt.objects.count(), StepAnswer.objects.count()) == (1, 1)

    def test_client_verdict_is_never_trusted(self, auth_client, exercise):
        answers = [self.offline_answer("s1", WRONG["s1"], minutes_ago=5) | {"is_correct": True}]

        response = auth_client.post("/api/sync/", self.payload(exercise, answers), format="json")

        assert response.data["attempts"][0]["answers"][0]["is_correct"] is False

    def test_invalid_answer_does_not_block_the_rest(self, auth_client, exercise):
        answers = [
            self.offline_answer("s1", {"value": True}, minutes_ago=20),
            self.offline_answer("s1", RIGHT["s1"], minutes_ago=10),
        ]

        response = auth_client.post("/api/sync/", self.payload(exercise, answers), format="json")

        statuses = [a["status"] for a in response.data["attempts"][0]["answers"]]
        assert statuses == ["rejected", "accepted"]

    def test_other_students_exercise_is_rejected(self, auth_client, other_user):
        foreign = make_exercise(other_user)

        response = auth_client.post(
            "/api/sync/", self.payload(foreign, [self.offline_answer("s1", RIGHT["s1"], 5)]), format="json"
        )

        assert response.data["attempts"][0]["status"] == "rejected"
        assert not Attempt.objects.exists()

    def test_online_and_offline_answers_mix(self, auth_client, attempt, exercise):
        answer(auth_client, attempt, "s1", RIGHT["s1"])

        response = auth_client.post(
            "/api/sync/",
            self.payload(exercise, [self.offline_answer("s2", RIGHT["s2"], 0)], attempt_id=str(attempt.id)),
            format="json",
        )

        assert response.data["attempts"][0]["attempt"]["score"] == 100

    def test_too_many_attempts(self, auth_client, exercise):
        payload = {"attempts": self.payload(exercise, [])["attempts"] * 51}

        assert auth_client.post("/api/sync/", payload, format="json").status_code == 400

    def test_requires_authentication(self, api_client):
        assert api_client.post("/api/sync/", {"attempts": []}, format="json").status_code == 401
