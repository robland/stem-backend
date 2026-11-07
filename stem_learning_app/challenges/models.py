import secrets
import uuid

from django.conf import settings
from django.db import models

# Sans caractères ambigus (0/O, 1/I/L) : le code se dicte et se recopie à la main.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class Challenge(models.Model):
    """Parcours partagé par son auteur. Seul l'énoncé retranscrit (et le parcours qui en découle) est partagé."""

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Privé"

    class Status(models.TextChoices):
        PENDING = "pending", "En vérification"
        ACTIVE = "active", "Actif"
        REJECTED = "rejected", "Refusé"
        HIDDEN = "hidden", "Masqué (signalements)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exercise = models.ForeignKey("learning.Exercise", on_delete=models.CASCADE, related_name="challenges")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenges")
    visibility = models.CharField(max_length=10, choices=Visibility.choices)
    # Partage (lien ou code dicté) ; seul moyen de rejoindre un défi privé.
    code = models.CharField(max_length=CODE_LENGTH, unique=True, default=new_code)
    # Chrono affiché pendant la résolution ; la durée départage toujours les ex aequo.
    timed = models.BooleanField(default=False)
    hints_allowed = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    # Motifs du refus automatique (llm.schemas.moderation), sans texte libre.
    moderation_reasons = models.JSONField(default=list, blank=True)
    moderation_prompt_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["visibility", "status", "-created_at"])]

    def __str__(self):
        return f"Défi {self.code} — {self.exercise}"


class ChallengeReport(models.Model):
    """Signalement d'un défi : un par élève, sans texte libre (aucune donnée personnelle à modérer)."""

    class Reason(models.TextChoices):
        INAPPROPRIATE = "inappropriate", "Contenu inapproprié"
        PERSONAL_DATA = "personal_data", "Données personnelles"
        WRONG_CONTENT = "wrong_content", "Correction fausse"
        OTHER = "other", "Autre"

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenge_reports")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["challenge", "reporter"], name="one_report_per_student"),
        ]

    def __str__(self):
        return f"{self.get_reason_display()} — {self.challenge}"
