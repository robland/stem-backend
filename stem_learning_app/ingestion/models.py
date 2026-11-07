import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from curriculum.choices import Level


def upload_path(instance, filename):
    # Nom aléatoire : le nom d'origine peut contenir le nom de l'élève.
    extension = "pdf" if instance.file_type == Upload.FileType.PDF else "img"
    return f"uploads/{instance.created_at_or_now:%Y/%m}/{uuid.uuid4().hex}.{extension}"


class Upload(models.Model):
    """
    Document envoyé par un élève. Le fichier est supprimé une fois l'extraction
    validée : il peut contenir le nom ou l'écriture de l'élève.
    """

    class FileType(models.TextChoices):
        IMAGE = "image", "Image"
        PDF = "pdf", "PDF"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        READING = "reading", "Lecture en cours"
        EXTRACTED = "extracted", "Énoncés extraits"
        ERROR = "error", "Erreur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploads")
    file = models.FileField(upload_to=upload_path, blank=True)
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    file_size = models.PositiveIntegerField()  # en octets
    file_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Message destiné à l'élève (jamais de détail technique).
    error_message = models.TextField(blank=True)
    # Prompt ayant produit l'extraction (ex. « extraction.v1 »), pour la traçabilité.
    prompt_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "file_hash"], name="unique_upload_per_user"),
        ]

    def __str__(self):
        return f"Upload {self.id} ({self.get_status_display()})"

    @property
    def created_at_or_now(self):
        return self.created_at or timezone.now()


class ExtractedExercise(models.Model):
    """Énoncé retranscrit depuis un upload, corrigeable par l'élève avant génération."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="exercises")
    order = models.PositiveSmallIntegerField()
    # Texte riche : texte + LaTeX $…$ / $$…$$ + \ce{…}. Jamais de HTML.
    statement = models.TextField()
    subject = models.ForeignKey("curriculum.Subject", on_delete=models.PROTECT, null=True, blank=True)
    chapter = models.ForeignKey("curriculum.Chapter", on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=4, choices=Level.choices, blank=True)
    # Thème proposé par le LLM quand aucun chapitre du référentiel ne correspond.
    chapter_hint = models.CharField(max_length=200, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["upload", "order"]
        constraints = [
            models.UniqueConstraint(fields=["upload", "order"], name="unique_extracted_exercise_order"),
        ]

    def __str__(self):
        return f"Exercice {self.order} de {self.upload_id}"
