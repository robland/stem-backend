"""Tentatives : réponses, indices, progression et score (README §5.2).

Logique commune aux endpoints en ligne et à la synchronisation hors-ligne : le
serveur recorrige toujours les réponses reçues.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from grading.engine import GradeResult, InvalidResponse, grade_step
from llm.schemas import ExerciseContent

from .models import Attempt, Exercise, StepAnswer

PENALTY_PER_HINT = 20
PENALTY_PER_WRONG_ANSWER = 20


class AttemptError(Exception):
    """Action refusée ; le message s'adresse au client (HTTP 400)."""


class StepStatus:
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class StepState:
    step_id: str
    status: str = StepStatus.PENDING
    wrong_answers: int = 0
    hints_used: int = 0

    @property
    def closed(self):
        return self.status != StepStatus.PENDING

    @property
    def score(self):
        if self.status != StepStatus.SUCCEEDED:
            return 0
        return max(0, 100 - PENALTY_PER_HINT * self.hints_used - PENALTY_PER_WRONG_ANSWER * self.wrong_answers)


@dataclass
class AnswerOutcome:
    answer: StepAnswer
    result: GradeResult
    state: StepState
    explanation: str | None
    created: bool


# --- Démarrage -------------------------------------------------------------------

def start_attempt(user, exercise, attempt_id=None, started_at=None):
    """Renvoie (attempt, created). `attempt_id` fourni par le client rend l'appel idempotent."""
    if exercise.owner_id != user.id:
        # V1 : uniquement ses propres parcours (défis en V2).
        raise AttemptError("Parcours introuvable.")
    if exercise.generation_status != Exercise.GenerationStatus.READY:
        raise AttemptError("Ce parcours n'est pas encore prêt.")
    if attempt_id:
        existing = Attempt.objects.filter(id=attempt_id).first()
        if existing:
            if existing.user_id != user.id or existing.exercise_id != exercise.id:
                raise AttemptError("Identifiant de tentative déjà utilisé.")
            return existing, False
    attempt = Attempt(user=user, exercise=exercise, started_at=_not_in_future(started_at))
    if attempt_id:
        attempt.id = attempt_id
    attempt.save(force_insert=True)
    return attempt, True


# --- État ------------------------------------------------------------------------

def load_content(attempt):
    return ExerciseContent.model_validate(attempt.exercise.content)


def step_states(attempt, content=None):
    """État de chaque étape, dans l'ordre du parcours, recalculé depuis les réponses enregistrées."""
    content = content or load_content(attempt)
    states = {step.id: StepState(step.id, hints_used=attempt.hints.get(step.id, 0)) for step in content.steps}
    for answer in attempt.answers.order_by("answered_at", "received_at"):
        state = states.get(answer.step_id)
        if state is None or state.closed:
            continue
        state.hints_used = max(state.hints_used, answer.hints_used)
        if answer.is_correct:
            state.status = StepStatus.SUCCEEDED
        else:
            state.wrong_answers += 1
            if state.wrong_answers >= settings.ATTEMPT_MAX_WRONG_ANSWERS:
                state.status = StepStatus.FAILED
    return list(states.values())


def current_step_id(states):
    return next((state.step_id for state in states if not state.closed), None)


def _refresh_totals(attempt, states):
    attempt.score = round(sum(state.score for state in states) / len(states)) if states else 0
    attempt.hints_used = sum(state.hints_used for state in states)
    just_finished = all(state.closed for state in states) and not attempt.finished_at
    if just_finished:
        attempt.finished_at = timezone.now()
    attempt.save(update_fields=["score", "hints_used", "finished_at", "hints"])
    if just_finished:
        from .progress import on_attempt_finished

        on_attempt_finished(attempt)


# --- Réponses --------------------------------------------------------------------

def submit_answer(attempt, *, step_id, response, client_uuid, answered_at=None, hints_used=None):
    """Corrige et enregistre une réponse. Idempotent par `client_uuid`."""
    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().select_related("exercise").get(id=attempt.id)
        content = load_content(attempt)
        steps = {step.id: step for step in content.steps}

        existing = StepAnswer.objects.filter(client_uuid=client_uuid).first()
        if existing:
            if existing.attempt_id != attempt.id:
                raise AttemptError("Identifiant de réponse déjà utilisé.")
            states = step_states(attempt, content)
            state = next(s for s in states if s.step_id == existing.step_id)
            result = grade_step(steps[existing.step_id], existing.response)
            return AnswerOutcome(existing, result, state, _explanation(steps, state), created=False)

        if attempt.finished_at:
            raise AttemptError("Cette tentative est terminée.")
        if step_id not in steps:
            raise AttemptError("Étape inconnue.")
        states = step_states(attempt, content)
        if step_id != current_step_id(states):
            raise AttemptError("Réponds aux étapes dans l'ordre : cette étape n'est pas l'étape en cours.")

        try:
            result = grade_step(steps[step_id], response)
        except InvalidResponse as e:
            raise AttemptError(str(e))

        # Indices consultés hors-ligne : on garde le maximum connu.
        offline_hints = min(hints_used or 0, len(steps[step_id].hints))
        if offline_hints > attempt.hints.get(step_id, 0):
            attempt.hints[step_id] = offline_hints
        answer = StepAnswer.objects.create(
            attempt=attempt,
            step_id=step_id,
            response=response,
            is_correct=result.is_correct,
            hints_used=attempt.hints.get(step_id, 0),
            answered_at=_not_in_future(answered_at),
            client_uuid=client_uuid,
        )
        states = step_states(attempt, content)
        _refresh_totals(attempt, states)
        state = next(s for s in states if s.step_id == step_id)
        return AnswerOutcome(answer, result, state, _explanation(steps, state), created=True)


def _explanation(steps, state):
    # La correction rédigée n'est donnée qu'une fois l'étape close (réussie ou échouée).
    return steps[state.step_id].explanation if state.closed else None


# --- Indices ---------------------------------------------------------------------

def next_hint(attempt, step_id):
    """Renvoie (texte, niveau 1..3) et le comptabilise ; le dernier niveau n'est donné que par ici."""
    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().select_related("exercise").get(id=attempt.id)
        if attempt.finished_at:
            raise AttemptError("Cette tentative est terminée.")
        content = load_content(attempt)
        steps = {step.id: step for step in content.steps}
        if step_id not in steps:
            raise AttemptError("Étape inconnue.")
        states = step_states(attempt, content)
        if step_id != current_step_id(states):
            raise AttemptError("Les indices ne concernent que l'étape en cours.")

        hints = steps[step_id].hints
        level = attempt.hints.get(step_id, 0)
        if level >= len(hints):
            raise AttemptError("Tous les indices de cette étape ont déjà été donnés.")
        attempt.hints[step_id] = level + 1
        _refresh_totals(attempt, step_states(attempt, content))
        return hints[level], level + 1, len(hints)


def _not_in_future(moment):
    now = timezone.now()
    return min(moment, now) if moment else now


# --- Synchronisation hors-ligne ----------------------------------------------------

def sync_attempts(user, attempts):
    """Rejoue des tentatives faites hors-ligne. Idempotent : ids de tentative et `client_uuid` fournis par le client.

    Chaque réponse est recorrigée par le serveur ; une réponse refusée n'empêche pas les suivantes.
    """
    results = []
    for item in attempts:
        exercise = Exercise.objects.filter(id=item["exercise"], owner=user).first()
        try:
            if exercise is None:
                raise AttemptError("Parcours introuvable.")
            attempt, _ = start_attempt(user, exercise, item["id"], item["started_at"])
        except AttemptError as e:
            results.append({"id": item["id"], "status": "rejected", "reason": str(e), "attempt": None, "answers": []})
            continue

        answers = []
        for data in sorted(item["answers"], key=lambda a: a["answered_at"]):
            try:
                outcome = submit_answer(
                    attempt,
                    step_id=data["step_id"],
                    response=data["response"],
                    client_uuid=data["client_uuid"],
                    answered_at=data["answered_at"],
                    hints_used=data.get("hints_used"),
                )
            except AttemptError as e:
                answers.append({"client_uuid": data["client_uuid"], "status": "rejected", "is_correct": None,
                                "reason": str(e)})
                continue
            answers.append({
                "client_uuid": data["client_uuid"],
                "status": "accepted" if outcome.created else "duplicate",
                "is_correct": outcome.result.is_correct,
                "reason": None,
            })
        attempt.refresh_from_db()
        results.append({"id": attempt.id, "status": "synced", "reason": None, "attempt": attempt, "answers": answers})
    return results
