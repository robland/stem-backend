"""Progression de l'élève : maîtrise par chapitre, révision espacée, série de jours (README §5.3).

La révision est planifiée par parcours à partir de l'historique des tentatives
(intervalles type Leitner) : elle fonctionne même sans chapitre rattaché.
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from .models import Attempt, Exercise, Mastery, StepAnswer

MASTERED_SCORE = 80
IN_PROGRESS_SCORE = 40
# Poids de la dernière tentative dans le score de maîtrise (moyenne mobile).
LATEST_WEIGHT = 0.4
MAX_INTERVAL_DAYS = 60
REVIEW_LIMIT = 10
STREAK_LOOKBACK_DAYS = 400


# --- Révision espacée ------------------------------------------------------------

def review_interval(scores):
    """Intervalle (jours) avant la prochaine révision, d'après les scores successifs.

    ≥ 80 : intervalle doublé (1 jour la première fois) ; 50–79 : intervalle conservé ;
    < 50 : retour à 1 jour.
    """
    interval = 0
    for score in scores:
        if score >= MASTERED_SCORE:
            interval = min(max(1, interval * 2), MAX_INTERVAL_DAYS)
        elif score < 50:
            interval = 1
        else:
            interval = max(1, interval)
    return max(1, interval)


def exercise_reviews(user):
    """Pour chaque parcours de l'élève : dernière tentative finie, dernier score, échéance de révision."""
    history = defaultdict(list)
    for exercise_id, finished_at, score in (
        Attempt.objects.filter(user=user, finished_at__isnull=False)
        .order_by("finished_at")
        .values_list("exercise_id", "finished_at", "score")
    ):
        history[exercise_id].append((finished_at, score))

    reviews = {}
    for exercise_id, attempts in history.items():
        last_finished, last_score = attempts[-1]
        interval = review_interval(score for _, score in attempts)
        reviews[exercise_id] = {
            "last_score": last_score,
            "last_finished_at": last_finished,
            "due_at": last_finished + timedelta(days=interval),
        }
    return reviews


def end_of_today():
    return timezone.localtime().replace(hour=23, minute=59, second=59, microsecond=999999)


def review_today(user):
    """Parcours à reprendre aujourd'hui : tentatives commencées non finies, puis révisions échues."""
    reviews = exercise_reviews(user)
    exercises = {
        e.id: e
        for e in Exercise.objects.filter(owner=user, generation_status=Exercise.GenerationStatus.READY)
        .select_related("subject", "chapter")
    }
    items = []

    unfinished = (
        Attempt.objects.filter(user=user, finished_at__isnull=True, exercise_id__in=exercises)
        .order_by("exercise_id", "-started_at")
    )
    seen = set()
    for attempt in unfinished:
        review = reviews.get(attempt.exercise_id)
        # Une tentative abandonnée avant une tentative finie plus récente n'est plus à reprendre.
        if attempt.exercise_id in seen or (review and review["last_finished_at"] > attempt.started_at):
            continue
        seen.add(attempt.exercise_id)
        items.append({
            "reason": "to_finish", "exercise": exercises[attempt.exercise_id], "attempt": attempt.id,
            "due_at": attempt.started_at, "last_score": review["last_score"] if review else None,
        })

    limit = end_of_today()
    for exercise_id, review in reviews.items():
        if exercise_id in seen or exercise_id not in exercises or review["due_at"] > limit:
            continue
        items.append({
            "reason": "to_review", "exercise": exercises[exercise_id], "attempt": None,
            "due_at": review["due_at"], "last_score": review["last_score"],
        })

    items.sort(key=lambda item: (item["reason"] != "to_finish", item["due_at"]))
    return items[:REVIEW_LIMIT]


# --- Maîtrise par chapitre ----------------------------------------------------------

def state_for(score):
    if score >= MASTERED_SCORE:
        return Mastery.State.MASTERED
    if score >= IN_PROGRESS_SCORE:
        return Mastery.State.IN_PROGRESS
    return Mastery.State.NOT_ACQUIRED


def on_attempt_finished(attempt):
    """Met à jour la maîtrise du chapitre du parcours (s'il en a un)."""
    chapter_id = attempt.exercise.chapter_id
    if not chapter_id:
        return
    mastery, created = Mastery.objects.get_or_create(user=attempt.user, chapter_id=chapter_id)
    mastery.score = attempt.score if created else round(
        (1 - LATEST_WEIGHT) * mastery.score + LATEST_WEIGHT * attempt.score
    )
    mastery.state = state_for(mastery.score)
    # Prochaine révision du chapitre : la plus proche échéance de ses parcours.
    chapter_exercises = set(
        Exercise.objects.filter(owner=attempt.user, chapter_id=chapter_id).values_list("id", flat=True)
    )
    due_dates = [
        review["due_at"] for exercise_id, review in exercise_reviews(attempt.user).items()
        if exercise_id in chapter_exercises
    ]
    mastery.next_review_at = min(due_dates) if due_dates else None
    mastery.save()


# --- Synthèse -----------------------------------------------------------------------

def streak_days(user):
    """Jours consécutifs (fuseau local) avec au moins une réponse, jusqu'à aujourd'hui ou hier."""
    since = timezone.now() - timedelta(days=STREAK_LOOKBACK_DAYS)
    days = {
        timezone.localtime(moment).date()
        for moment in StepAnswer.objects.filter(attempt__user=user, answered_at__gte=since)
        .values_list("answered_at", flat=True)
    }
    day = timezone.localdate()
    if day not in days:
        day -= timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def progress_summary(user):
    from challenges.services import author_points  # challenges dépend de learning

    # order_by() : l'ordre par défaut (-started_at) fausserait les DISTINCT.
    finished = Attempt.objects.filter(user=user, finished_at__isnull=False).order_by()
    by_subject = (
        finished.values("exercise__subject__code")
        .annotate(average=Avg("score"))
        .order_by("exercise__subject__code")
    )
    exercises_by_subject = defaultdict(int)
    for code in finished.values_list("exercise__subject__code", "exercise_id").distinct():
        exercises_by_subject[code[0]] += 1
    average = finished.aggregate(average=Avg("score"))["average"]

    return {
        "summary": {
            "exercises_done": finished.values("exercise_id").distinct().count(),
            "attempts_finished": finished.count(),
            "average_score": round(average) if average is not None else None,
            "streak_days": streak_days(user),
            "author_points": author_points(user),
        },
        "subjects": [
            {
                "subject": row["exercise__subject__code"],
                "exercises_done": exercises_by_subject[row["exercise__subject__code"]],
                "average_score": round(row["average"]),
            }
            for row in by_subject
        ],
        "chapters": list(
            Mastery.objects.filter(user=user).select_related("chapter__subject").order_by("next_review_at")
        ),
        "review_today": review_today(user),
    }
