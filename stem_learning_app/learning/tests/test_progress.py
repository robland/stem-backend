import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from curriculum.models import Chapter, Subject
from learning.models import Attempt, Exercise, Mastery, StepAnswer
from learning.progress import review_interval, state_for, streak_days

from .test_attempts import RIGHT, WRONG, answer, make_exercise

pytestmark = pytest.mark.django_db

URL = "/api/progress/"


@pytest.fixture
def chapter():
    return Chapter.objects.create(subject=Subject.objects.get(code="maths"), level="3e", name="Calcul littéral")


def play(client, exercise, responses):
    """Joue une tentative complète en ligne ; `responses` = réponses successives (étape en cours)."""
    attempt_id = client.post(f"/api/exercises/{exercise.id}/attempts/", {}, format="json").data["id"]
    attempt = Attempt.objects.get(id=attempt_id)
    for step_id, response in responses:
        answer(client, attempt, step_id, response)
    attempt.refresh_from_db()
    return attempt


PERFECT = [("s1", RIGHT["s1"]), ("s2", RIGHT["s2"])]
FAILED = [("s1", WRONG["s1"])] * 3 + [("s2", WRONG["s2"])] * 3


def age(attempt, days):
    """Antidate une tentative finie (et ses réponses)."""
    moment = timezone.now() - timedelta(days=days)
    Attempt.objects.filter(id=attempt.id).update(started_at=moment, finished_at=moment)
    StepAnswer.objects.filter(attempt=attempt).update(answered_at=moment)


class TestReviewInterval:
    @pytest.mark.parametrize(
        "scores, expected",
        [([100], 1), ([100, 90], 2), ([100, 90, 85], 4), ([100, 100, 30], 1), ([100, 100, 60], 2), ([10], 1),
         ([100] * 10, 60)],
    )
    def test_leitner(self, scores, expected):
        assert review_interval(scores) == expected

    @pytest.mark.parametrize("score, state", [(85, "maitrise"), (80, "maitrise"), (50, "en_cours"), (39, "non_acquis")])
    def test_state(self, score, state):
        assert state_for(score) == state


class TestProgress:
    def test_requires_authentication(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_empty(self, auth_client):
        data = auth_client.get(URL).data

        assert data["summary"] == {
            "exercises_done": 0, "attempts_finished": 0, "average_score": None, "streak_days": 0, "author_points": 0,
        }
        assert data["subjects"] == data["chapters"] == data["review_today"] == []

    def test_summary_and_subjects(self, auth_client, user):
        exercise = make_exercise(user)
        play(auth_client, exercise, PERFECT)
        play(auth_client, exercise, FAILED)

        data = auth_client.get(URL).data

        assert data["summary"] == {
            "exercises_done": 1, "attempts_finished": 2, "average_score": 50, "streak_days": 1, "author_points": 0,
        }
        assert data["subjects"] == [{"subject": "maths", "exercises_done": 1, "average_score": 50}]

    def test_only_own_progress(self, auth_client, other_client, user, other_user):
        play(other_client, make_exercise(other_user), PERFECT)

        assert auth_client.get(URL).data["summary"]["attempts_finished"] == 0


class TestReviewToday:
    def test_unfinished_attempt_comes_first(self, auth_client, user):
        done = make_exercise(user)
        play(auth_client, done, FAILED)
        started = make_exercise(user)
        attempt = play(auth_client, started, [("s1", RIGHT["s1"])])

        items = auth_client.get(URL).data["review_today"]

        assert [(i["reason"], i["exercise"]["id"]) for i in items[:1]] == [("to_finish", str(started.id))]
        assert items[0]["attempt"] == str(attempt.id)

    def test_failed_exercise_is_due_the_next_day(self, auth_client, user):
        attempt = play(auth_client, make_exercise(user), FAILED)

        assert auth_client.get(URL).data["review_today"] == []

        age(attempt, days=1)
        [item] = auth_client.get(URL).data["review_today"]
        assert (item["reason"], item["last_score"]) == ("to_review", 0)

    def test_mastered_exercise_comes_back_later(self, auth_client, user):
        exercise = make_exercise(user)
        for days in (10, 8):  # deux réussites → intervalle de 2 jours après la dernière
            age(play(auth_client, exercise, PERFECT), days=days)

        assert len(auth_client.get(URL).data["review_today"]) == 1

        age(play(auth_client, exercise, PERFECT), days=1)  # troisième réussite → 4 jours
        assert auth_client.get(URL).data["review_today"] == []

    def test_abandoned_attempt_before_a_finished_one_is_ignored(self, auth_client, user):
        exercise = make_exercise(user)
        old = play(auth_client, exercise, [("s1", RIGHT["s1"])])
        Attempt.objects.filter(id=old.id).update(started_at=timezone.now() - timedelta(days=3))
        play(auth_client, exercise, PERFECT)

        assert auth_client.get(URL).data["review_today"] == []

    def test_exercise_not_ready_is_ignored(self, auth_client, user):
        exercise = make_exercise(user)
        age(play(auth_client, exercise, FAILED), days=2)
        Exercise.objects.filter(id=exercise.id).update(generation_status=Exercise.GenerationStatus.NEEDS_REVIEW)

        assert auth_client.get(URL).data["review_today"] == []

    def test_limit(self, auth_client, user):
        for _ in range(12):
            play(auth_client, make_exercise(user), [("s1", RIGHT["s1"])])

        assert len(auth_client.get(URL).data["review_today"]) == 10


class TestMastery:
    def test_created_and_updated_when_attempt_finishes(self, auth_client, user, chapter):
        exercise = make_exercise(user)
        exercise.chapter = chapter
        exercise.save()

        play(auth_client, exercise, PERFECT)
        mastery = Mastery.objects.get(user=user, chapter=chapter)
        assert (mastery.score, mastery.state) == (100, Mastery.State.MASTERED)
        assert mastery.next_review_at > timezone.now()

        play(auth_client, exercise, FAILED)
        mastery.refresh_from_db()
        assert (mastery.score, mastery.state) == (60, Mastery.State.IN_PROGRESS)  # 0,6 × 100 + 0,4 × 0

        [item] = auth_client.get(URL).data["chapters"]
        assert item["chapter"]["name"] == "Calcul littéral"
        assert (item["score"], item["state"]) == (60, "en_cours")

    def test_unfinished_attempt_does_not_count(self, auth_client, user, chapter):
        exercise = make_exercise(user)
        exercise.chapter = chapter
        exercise.save()

        play(auth_client, exercise, [("s1", RIGHT["s1"])])

        assert not Mastery.objects.exists()

    def test_exercise_without_chapter(self, auth_client, user):
        play(auth_client, make_exercise(user), PERFECT)

        assert not Mastery.objects.exists()

    def test_offline_sync_updates_mastery(self, auth_client, user, chapter):
        exercise = make_exercise(user)
        exercise.chapter = chapter
        exercise.save()
        now = timezone.now()
        payload = {"attempts": [{
            "id": str(uuid.uuid4()), "exercise": str(exercise.id), "started_at": now.isoformat(),
            "answers": [
                {"client_uuid": str(uuid.uuid4()), "step_id": step_id, "response": response,
                 "answered_at": (now + timedelta(seconds=i)).isoformat()}
                for i, (step_id, response) in enumerate(PERFECT)
            ],
        }]}

        auth_client.post("/api/sync/", payload, format="json")

        assert Mastery.objects.get().score == 100


class TestStreak:
    def test_consecutive_days(self, auth_client, user):
        for days in (0, 1, 2, 4):
            age(play(auth_client, make_exercise(user), PERFECT), days=days)

        assert streak_days(user) == 3

    def test_streak_still_counts_if_not_played_today(self, auth_client, user):
        for days in (1, 2):
            age(play(auth_client, make_exercise(user), PERFECT), days=days)

        assert streak_days(user) == 2

    def test_broken_streak(self, auth_client, user):
        age(play(auth_client, make_exercise(user), PERFECT), days=2)

        assert streak_days(user) == 0
