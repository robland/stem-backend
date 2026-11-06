import logging
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from curriculum.models import Chapter, Subject
from llm.exceptions import LLMError, LLMRefusal
from llm.services import extract_exercises

from .documents import DocumentError, to_llm_images
from .models import ExtractedExercise, Upload

logger = logging.getLogger(__name__)

ERROR_NO_EXERCISE = "Aucun exercice détecté. Vérifie que la photo est nette et cadrée sur l'énoncé."
ERROR_REFUSED = "Ce document ne peut pas être analysé."
ERROR_LLM = "L'analyse a échoué. Réessaie dans quelques minutes en renvoyant le document."
ERROR_FILE_MISSING = "Le document n'est plus disponible : renvoie-le."


# --- Quota -------------------------------------------------------------------

def _start_of_today():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def uploads_left_today(user):
    used = Upload.objects.filter(user=user, created_at__gte=_start_of_today()).count()
    return max(settings.UPLOAD_DAILY_QUOTA - used, 0)


def seconds_until_quota_reset():
    tomorrow = timezone.localdate() + timedelta(days=1)
    reset = timezone.make_aware(datetime.combine(tomorrow, time.min))
    return int((reset - timezone.now()).total_seconds()) + 1


# --- Extraction --------------------------------------------------------------

def run_extraction(upload_id):
    """Étape asynchrone : document → énoncés. Idempotente (ne traite qu'un upload en attente)."""
    updated = Upload.objects.filter(id=upload_id, status=Upload.Status.PENDING).update(
        status=Upload.Status.READING, updated_at=timezone.now()
    )
    if not updated:
        return
    upload = Upload.objects.select_related("user").get(id=upload_id)

    try:
        if not upload.file:
            raise DocumentError(ERROR_FILE_MISSING)
        with upload.file.open("rb") as f:
            images = to_llm_images(f.read(), upload.file_type)
        result = extract_exercises(images, declared_level=upload.user.level)
    except DocumentError as e:
        return _fail(upload, str(e))
    except LLMRefusal:
        return _fail(upload, ERROR_REFUSED)
    except LLMError:
        logger.exception("Extraction en échec pour l'upload %s", upload.id)
        return _fail(upload, ERROR_LLM)

    output = result.output
    if not output.is_exercise_document or not output.exercises:
        return _fail(upload, ERROR_NO_EXERCISE)

    subjects = {s.code: s for s in Subject.objects.all()}
    with transaction.atomic():
        for order, item in enumerate(output.exercises):
            subject = subjects.get(item.subject) if item.subject else None
            level = item.level or upload.user.level
            ExtractedExercise.objects.create(
                upload=upload,
                order=order,
                statement=item.statement,
                subject=subject,
                level=level,
                chapter=_match_chapter(subject, level, item.chapter_hint),
                chapter_hint=item.chapter_hint or "",
            )
        upload.status = Upload.Status.EXTRACTED
        upload.prompt_id = result.prompt_id
        upload.error_message = ""
        upload.save(update_fields=["status", "prompt_id", "error_message", "updated_at"])


def _match_chapter(subject, level, hint):
    if not (subject and level and hint):
        return None
    return Chapter.objects.filter(subject=subject, level=level, name__iexact=hint.strip()).first()


def _fail(upload, message):
    upload.status = Upload.Status.ERROR
    upload.error_message = message
    upload.save(update_fields=["status", "error_message", "updated_at"])
    # Aucune relance possible sur cet upload : le fichier n'a plus de raison d'être conservé.
    delete_file(upload)


# --- Validation & suppression du fichier ----------------------------------------

def validate_exercise(exercise):
    exercise.validated_at = timezone.now()
    exercise.save(update_fields=["validated_at"])
    delete_file_if_done(exercise.upload)


def delete_file_if_done(upload):
    """Le fichier est supprimé dès que tous les énoncés restants sont validés."""
    if not upload.exercises.filter(validated_at__isnull=True).exists():
        delete_file(upload)


def delete_file(upload):
    if upload.file:
        upload.file.delete(save=False)
        Upload.objects.filter(id=upload.id).update(file="")


def purge_expired_files():
    """Supprime les fichiers conservés au-delà de UPLOAD_FILE_RETENTION_HOURS. Renvoie leur nombre."""
    limit = timezone.now() - timedelta(hours=settings.UPLOAD_FILE_RETENTION_HOURS)
    expired = Upload.objects.filter(created_at__lt=limit).exclude(file="")
    count = 0
    for upload in expired:
        delete_file(upload)
        count += 1
    return count
