"""Défis (README §5.4) : création, modération, participation, signalements, classement, points de l'auteur."""

import copy
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from ingestion.services import stuck_before
from learning.models import Attempt, Exercise
from learning.services import public_content
from llm.exceptions import LLMError
from llm.services import moderate_statement

from .models import Challenge, ChallengeReport, new_code

logger = logging.getLogger(__name__)

ACTIVE_OR_PENDING = (Challenge.Status.ACTIVE, Challenge.Status.PENDING)


class ChallengeError(Exception):
    """Action refusée ; le message s'adresse à l'élève (HTTP 400)."""


# --- Création et modération ---------------------------------------------------------

def create_challenge(author, exercise, *, visibility, timed=False, hints_allowed=True):
    """Privé : actif tout de suite. Public : en vérification jusqu'au verdict du LLM."""
    if exercise.owner_id != author.id:
        raise ChallengeError("Parcours introuvable.")
    if exercise.generation_status != Exercise.GenerationStatus.READY:
        raise ChallengeError("Ce parcours n'est pas prêt.")
    # « Une fois l'exercice travaillé » (README §1) : l'auteur l'a terminé au moins une fois.
    if not Attempt.objects.filter(user=author, exercise=exercise, challenge=None, finished_at__isnull=False).exists():
        raise ChallengeError("Termine d'abord ce parcours avant de le proposer en défi.")
    public = visibility == Challenge.Visibility.PUBLIC
    if public and exercise.content_hash and Challenge.objects.filter(
        visibility=Challenge.Visibility.PUBLIC, status__in=ACTIVE_OR_PENDING,
        exercise__content_hash=exercise.content_hash,
    ).exists():
        raise ChallengeError("Ce défi existe déjà dans le catalogue public.")

    challenge = Challenge(
        exercise=exercise, author=author, visibility=visibility, timed=timed, hints_allowed=hints_allowed,
        status=Challenge.Status.PENDING if public else Challenge.Status.ACTIVE,
    )
    _save_with_unique_code(challenge)
    if public:
        from .tasks import moderate_challenge_task

        transaction.on_commit(lambda: moderate_challenge_task.delay(str(challenge.id)))
    return challenge


def _save_with_unique_code(challenge, tries=5):
    for _ in range(tries):
        try:
            with transaction.atomic():
                challenge.save(force_insert=True)
            return
        except IntegrityError:
            if Challenge.objects.filter(code=challenge.code).exists():
                challenge.code = new_code()
                continue
            raise
    raise ChallengeError("Impossible de créer le défi, réessaie.")


def run_moderation(challenge_id):
    """Verdict du LLM sur l'énoncé d'un défi public en vérification. Idempotent ; un échec d'appel le laisse
    en vérification (relancé par la maintenance)."""
    challenge = Challenge.objects.select_related("exercise").filter(
        id=challenge_id, status=Challenge.Status.PENDING
    ).first()
    if challenge is None:
        return
    try:
        result = moderate_statement(challenge.exercise.content["statement"])
    except LLMError:
        logger.exception("Modération en échec pour le défi %s", challenge.id)
        return
    verdict = result.output
    challenge.status = Challenge.Status.ACTIVE if verdict.acceptable else Challenge.Status.REJECTED
    challenge.moderation_reasons = list(verdict.reasons)
    challenge.moderation_prompt_id = result.prompt_id
    challenge.save(update_fields=["status", "moderation_reasons", "moderation_prompt_id", "updated_at"])
    if not verdict.acceptable:
        logger.info("Défi %s refusé par la modération : %s", challenge.id, ", ".join(verdict.reasons))


def recover_pending_moderations():
    """Relance les modérations restées sans verdict (worker arrêté, échec d'appel). Renvoie leur nombre."""
    from .tasks import moderate_challenge_task

    pending = list(
        Challenge.objects.filter(status=Challenge.Status.PENDING, updated_at__lt=stuck_before())
        .values_list("id", flat=True)
    )
    Challenge.objects.filter(id__in=pending).update(updated_at=timezone.now())
    for challenge_id in pending:
        moderate_challenge_task.delay(str(challenge_id))
    return len(pending)


# --- Consultation ---------------------------------------------------------------------

def visible_to(user):
    """Défis consultables : publics actifs, les siens, ceux qu'on a rejoints."""
    # Sous-requête plutôt que jointure : une jointure sur `attempts` fausserait les comptes de with_counts.
    return Challenge.objects.filter(
        Q(visibility=Challenge.Visibility.PUBLIC, status=Challenge.Status.ACTIVE)
        | Q(author=user)
        | Q(id__in=joined_ids(user))
    )


def joined_ids(user):
    return Attempt.objects.filter(user=user, challenge__isnull=False).values("challenge_id")


def challenge_content(challenge):
    """Contenu public du parcours ; sans aucun indice si l'auteur les a désactivés."""
    content = public_content(challenge.exercise.content)
    if not challenge.hints_allowed:
        content = copy.deepcopy(content)
        for step in content.get("steps", []):
            step["hints"] = []
    return content


# --- Participation --------------------------------------------------------------------

def start_challenge_attempt(user, challenge, *, attempt_id=None, code=""):
    """Renvoie (attempt, created). Une seule tentative par élève : la relancer renvoie la même."""
    existing = Attempt.objects.filter(user=user, challenge=challenge).first()
    if existing:
        return existing, False
    if challenge.author_id == user.id:
        raise ChallengeError("Tu ne peux pas relever ton propre défi.")
    if challenge.status != Challenge.Status.ACTIVE:
        raise ChallengeError("Ce défi n'est pas disponible.")
    if challenge.visibility == Challenge.Visibility.PRIVATE and code.upper() != challenge.code:
        raise ChallengeError("Code du défi invalide.")
    if attempt_id and Attempt.objects.filter(id=attempt_id).exists():
        raise ChallengeError("Identifiant de tentative déjà utilisé.")

    # Heure du serveur, jamais celle du client : la durée départage le classement.
    attempt = Attempt(
        user=user, exercise=challenge.exercise, challenge=challenge, mode=Attempt.Mode.CHALLENGE,
        started_at=timezone.now(),
    )
    if attempt_id:
        attempt.id = attempt_id
    try:
        with transaction.atomic():
            attempt.save(force_insert=True)
    except IntegrityError:  # deux démarrages simultanés
        return Attempt.objects.get(user=user, challenge=challenge), False
    return attempt, True


def report_challenge(user, challenge, reason):
    """Un signalement par élève (renvoyer le même ne compte pas deux fois). Renvoie created."""
    if challenge.author_id == user.id:
        raise ChallengeError("Tu ne peux pas signaler ton propre défi.")
    _, created = ChallengeReport.objects.get_or_create(
        challenge=challenge, reporter=user, defaults={"reason": reason}
    )
    if created and challenge.status == Challenge.Status.ACTIVE:
        if challenge.reports.count() >= settings.CHALLENGE_REPORTS_TO_HIDE:
            challenge.status = Challenge.Status.HIDDEN
            challenge.save(update_fields=["status", "updated_at"])
            logger.warning("Défi %s masqué après signalements, à relire", challenge.id)
    return created


# --- Classement et points ---------------------------------------------------------------

def _duration(attempt):
    return attempt.finished_at - attempt.started_at


def leaderboard(challenge, user):
    """Participants ayant terminé : meilleur score, puis le plus rapide, puis le premier arrivé."""
    finished = sorted(
        Attempt.objects.filter(challenge=challenge, finished_at__isnull=False).select_related("user"),
        key=lambda a: (-a.score, _duration(a), a.finished_at),
    )
    entries = [
        {
            "rank": rank,
            "pseudo": attempt.user.pseudo,
            "score": attempt.score,
            "duration_seconds": round(_duration(attempt).total_seconds()),
            "is_me": attempt.user_id == user.id,
        }
        for rank, attempt in enumerate(finished, start=1)
    ]
    return {
        "participants": challenge.attempts.count(),
        "finished": len(entries),
        "entries": entries[: settings.CHALLENGE_LEADERBOARD_SIZE],
        "me": next((entry for entry in entries if entry["is_me"]), None),
    }


def points_for(finished_participants):
    return min(settings.CHALLENGE_AUTHOR_POINTS_MAX, settings.CHALLENGE_AUTHOR_POINTS_PER_FINISH * finished_participants)


def with_counts(queryset):
    return queryset.annotate(
        participants_count=Count("attempts", distinct=True),
        finished_count=Count("attempts", filter=Q(attempts__finished_at__isnull=False), distinct=True),
    )


def author_points(user):
    """Total des points gagnés par l'élève en tant qu'auteur de défis."""
    return sum(points_for(c.finished_count) for c in with_counts(Challenge.objects.filter(author=user)))
