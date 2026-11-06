import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from curriculum.choices import Level


class Exercise(models.Model):
    """
    Parcours guidé généré pour un énoncé. `content` suit le schéma d'activités
    (README §6) et est validé avant enregistrement.
    """

    class GenerationStatus(models.TextChoices):
        PENDING = "pending", "En attente"
        GENERATING = "generating", "Génération"
        READY = "ready", "Prêt"
        NEEDS_REVIEW = "needs_review", "À revoir"
        ERROR = "error", "Erreur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exercises")
    source = models.ForeignKey(
        "ingestion.ExtractedExercise", on_delete=models.SET_NULL, null=True, blank=True, related_name="parcours"
    )
    subject = models.ForeignKey("curriculum.Subject", on_delete=models.PROTECT, related_name="exercises")
    chapter = models.ForeignKey(
        "curriculum.Chapter", on_delete=models.SET_NULL, null=True, blank=True, related_name="exercises"
    )
    level = models.CharField(max_length=4, choices=Level.choices)
    title = models.CharField(max_length=255, blank=True)
    content = models.JSONField(default=dict)
    schema_version = models.CharField(max_length=10, blank=True)
    generation_status = models.CharField(
        max_length=20, choices=GenerationStatus.choices, default=GenerationStatus.PENDING
    )
    # Empreinte de l'énoncé normalisé : déduplication et cache de génération.
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or f"Parcours {self.id}"


class Attempt(models.Model):
    class Mode(models.TextChoices):
        SOLO = "solo", "Solo"
        CHALLENGE = "challenge", "Défi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="attempts")
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.SOLO)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    hints_used = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Tentative {self.id} — {self.user}"


class StepAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    step_id = models.CharField(max_length=50)
    response = models.JSONField()
    is_correct = models.BooleanField()
    hints_used = models.PositiveSmallIntegerField(default=0)
    # Heure de la réponse sur l'appareil (peut précéder la synchronisation hors-ligne).
    answered_at = models.DateTimeField()
    # Généré par le client : rend la synchronisation hors-ligne idempotente.
    client_uuid = models.UUIDField(unique=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["answered_at"]

    def __str__(self):
        return f"{self.step_id} ({'juste' if self.is_correct else 'faux'})"


class Mastery(models.Model):
    """Maîtrise d'un chapitre par un élève, base de la révision espacée."""

    class State(models.TextChoices):
        NOT_ACQUIRED = "non_acquis", "Non acquis"
        IN_PROGRESS = "en_cours", "En cours"
        MASTERED = "maitrise", "Maîtrisé"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="masteries")
    chapter = models.ForeignKey("curriculum.Chapter", on_delete=models.CASCADE, related_name="masteries")
    score = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    state = models.CharField(max_length=20, choices=State.choices, default=State.NOT_ACQUIRED)
    next_review_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "masteries"
        constraints = [
            models.UniqueConstraint(fields=["user", "chapter"], name="unique_mastery_per_chapter"),
            models.CheckConstraint(condition=models.Q(score__lte=100), name="mastery_score_max_100"),
        ]

    def __str__(self):
        return f"{self.user} — {self.chapter} : {self.get_state_display()}"
