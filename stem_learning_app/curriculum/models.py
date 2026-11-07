import uuid

from django.db import models

from .choices import Level, SubjectCode


class Subject(models.Model):
    """Matière du référentiel (figée, créée par migration)."""

    code = models.CharField(max_length=30, choices=SubjectCode.choices, unique=True)
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Chapter(models.Model):
    """Chapitre du programme congolais, propre à une matière et un niveau."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="chapters")
    level = models.CharField(max_length=4, choices=Level.choices)
    name = models.CharField(max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["subject__order", "level", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["subject", "level", "name"], name="unique_chapter_per_subject_level"),
        ]

    def __str__(self):
        return f"{self.subject} {self.level} — {self.name}"
