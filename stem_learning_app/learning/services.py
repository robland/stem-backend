import copy
import hashlib
import logging
import unicodedata

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from grading.verify import verify_exercise
from ingestion.services import seconds_until_quota_reset, start_of_today, stuck_before
from llm.exceptions import LLMError, LLMRefusal
from llm.schemas import SCHEMA_VERSION, ExerciseContent
from llm.services import generate_exercise

from .models import Exercise

logger = logging.getLogger(__name__)

ERROR_REFUSED = "Cet énoncé ne peut pas être transformé en parcours."
ERROR_LLM = "La préparation du parcours a échoué. Réessaie dans quelques minutes."
ERROR_NEEDS_REVIEW = "Ce parcours doit être vérifié avant de t'être proposé."
ERROR_INTERRUPTED = "La préparation du parcours a été interrompue. Relance-la."


class GenerationRefused(Exception):
    """Demande de génération impossible ; le message s'adresse à l'élève."""


class QuotaExceeded(Exception):
    def __init__(self, wait):
        super().__init__("Quota journalier de parcours atteint.")
        self.wait = wait


# --- Demande -------------------------------------------------------------------

def content_hash(statement, subject_code, level):
    """Empreinte insensible à la casse et aux espaces : clé du cache de génération."""
    normalized = " ".join(unicodedata.normalize("NFC", statement).lower().split())
    return hashlib.sha256(f"{subject_code}|{level}|{normalized}".encode()).hexdigest()


def generations_left_today(user):
    # Les copies issues du cache (prêtes, sans prompt) ne coûtent rien et ne comptent pas.
    used = (
        Exercise.objects.filter(owner=user, created_at__gte=start_of_today())
        .exclude(generation_status=Exercise.GenerationStatus.READY, prompt_id="")
        .count()
    )
    return max(settings.GENERATION_DAILY_QUOTA - used, 0)


def request_generation(extracted):
    """Énoncé validé → parcours. Renvoie (exercise, launched) ; `launched` si une génération démarre.

    Idempotent : un parcours existant (en cours ou prêt) est renvoyé tel quel ; un parcours
    en erreur est relancé. Un énoncé identique déjà traité est repris du cache sans appel LLM.
    """
    if not extracted.validated_at:
        raise GenerationRefused("Valide l'énoncé avant de lancer le parcours.")
    if extracted.subject.code not in settings.GENERATION_SUBJECTS:
        raise GenerationRefused(f"Les parcours ne sont pas encore disponibles en {extracted.subject.name}.")

    user = extracted.upload.user
    existing = Exercise.objects.filter(source=extracted).first()
    if existing and existing.generation_status != Exercise.GenerationStatus.ERROR:
        return existing, False

    digest = content_hash(extracted.statement, extracted.subject.code, extracted.level)
    cached = (
        Exercise.objects.filter(content_hash=digest, generation_status=Exercise.GenerationStatus.READY)
        .exclude(prompt_id="")
        .order_by("-created_at")
        .first()
    )

    # Relancer un parcours en erreur ne consomme pas de quota supplémentaire.
    if not cached and not existing and generations_left_today(user) == 0:
        raise QuotaExceeded(seconds_until_quota_reset())

    exercise = existing or Exercise(owner=user, source=extracted)
    exercise.subject = extracted.subject
    exercise.chapter = extracted.chapter
    exercise.level = extracted.level
    exercise.content_hash = digest
    exercise.error_message = ""

    if cached:
        exercise.title = cached.title
        exercise.content = copy.deepcopy(cached.content)
        exercise.schema_version = cached.schema_version
        exercise.prompt_id = ""
        exercise.generation_status = Exercise.GenerationStatus.READY
        exercise.save()
        return exercise, False

    exercise.generation_status = Exercise.GenerationStatus.PENDING
    exercise.save()

    from .tasks import generate_exercise_task

    transaction.on_commit(lambda: generate_exercise_task.delay(str(exercise.id)))
    return exercise, True


# --- Génération (asynchrone) ------------------------------------------------------

def run_generation(exercise_id):
    """Idempotente : ne traite qu'un parcours en attente."""
    updated = Exercise.objects.filter(id=exercise_id, generation_status=Exercise.GenerationStatus.PENDING).update(
        generation_status=Exercise.GenerationStatus.GENERATING, updated_at=timezone.now()
    )
    if not updated:
        return
    exercise = Exercise.objects.select_related("subject", "chapter", "source").get(id=exercise_id)
    statement = exercise.source.statement if exercise.source else ""
    if not statement:
        return _fail(exercise, ERROR_LLM)

    chapter = exercise.chapter.name if exercise.chapter else (exercise.source.chapter_hint or "")
    try:
        result, content, issues = generate_and_verify(statement, exercise.subject.code, exercise.level, chapter)
    except LLMRefusal:
        return _fail(exercise, ERROR_REFUSED)
    except LLMError:
        logger.exception("Génération en échec pour le parcours %s", exercise.id)
        return _fail(exercise, ERROR_LLM)

    exercise.title = content.title
    exercise.content = content.model_dump(mode="json")
    exercise.schema_version = SCHEMA_VERSION
    exercise.prompt_id = result.prompt_id
    exercise.review_notes = "\n".join(issues)
    if issues:
        logger.warning("Parcours %s à revoir : %d problème(s) après revérification", exercise.id, len(issues))
        exercise.generation_status = Exercise.GenerationStatus.NEEDS_REVIEW
        exercise.error_message = ERROR_NEEDS_REVIEW
    else:
        exercise.generation_status = Exercise.GenerationStatus.READY
    exercise.save()


def generate_and_verify(statement, subject_code, level, chapter=""):
    """Génère puis revérifie (justesse, couverture des questions) ; régénération ciblée si besoin.

    Renvoie (LLMResult, ExerciseContent, problèmes restants). Lève LLMError.
    """
    issues = []
    for _ in range(settings.GENERATION_ATTEMPTS):
        result = generate_exercise(
            statement=statement, subject=subject_code, level=level, chapter=chapter, corrections=issues,
        )
        content = build_content(result.output, statement)
        issues = verify_exercise(content)
        if not issues:
            break
    return result, content, issues


def build_content(generated, statement):
    """Contenu stocké (ExerciseContent) : sortie du LLM + énoncé validé par l'élève, revalidé en entier."""
    data = {"schema_version": SCHEMA_VERSION, "statement": statement, **generated.model_dump(mode="json")}
    try:
        return ExerciseContent.model_validate(data)
    except ValidationError:
        # L'énoncé a déjà été validé par les mêmes règles : ne devrait jamais arriver.
        logger.exception("Contenu de parcours invalide")
        raise


def _fail(exercise, message):
    exercise.generation_status = Exercise.GenerationStatus.ERROR
    exercise.error_message = message
    exercise.save(update_fields=["generation_status", "error_message", "updated_at"])


# --- Exposition (README §6.4) ------------------------------------------------------

def public_content(content):
    """Contenu sans ce qui donne la réponse : `answer`, erreurs typiques, correction, dernier indice."""
    content = copy.deepcopy(content)
    for step in content.get("steps", []):
        step["activity"].pop("answer", None)
        step.pop("common_mistakes", None)
        step.pop("explanation", None)
        step["hints"] = step["hints"][:-1]
    return content


def recover_stuck_generations():
    """Relance les générations jamais démarrées ; met en erreur celles interrompues (relance possible par l'élève,
    sans quota supplémentaire). Renvoie (relancées, en erreur)."""
    from .tasks import generate_exercise_task

    limit = stuck_before()
    pending = list(
        Exercise.objects.filter(generation_status=Exercise.GenerationStatus.PENDING, updated_at__lt=limit)
        .values_list("id", flat=True)
    )
    Exercise.objects.filter(id__in=pending).update(updated_at=timezone.now())
    for exercise_id in pending:
        generate_exercise_task.delay(str(exercise_id))

    interrupted = Exercise.objects.filter(generation_status=Exercise.GenerationStatus.GENERATING, updated_at__lt=limit)
    failed = 0
    for exercise in interrupted:
        logger.warning("Génération interrompue pour le parcours %s", exercise.id)
        _fail(exercise, ERROR_INTERRUPTED)
        failed += 1
    return len(pending), failed
