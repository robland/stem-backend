from django.db import models
import uuid


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("image", "Image"),
        ("pdf", "PDF"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)

    file = models.FileField(upload_to="documents/")
    file_type = models.CharField(max_length=10, choices=DOCUMENT_TYPE_CHOICES)

    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # en octets

    file_hash = models.CharField(max_length=64, unique=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    processing_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "En attente"),
            ("analyzing", "Analyse"),
            ("generating", "Génération QCM"),
            ("done", "Terminé"),
            ("error", "Erreur"),
        ]
    )

    def __str__(self):
        return self.original_filename


class Subject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=25, default="")

    def __str__(self):
        return self.name


class Chapter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='chapters')

    def __str__(self):
        return self.name


class Exercise(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        related_name="exercises",
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255, blank=True)
    statement = models.TextField()
    chapter = models.ForeignKey('Chapter', on_delete=models.CASCADE)
    level = models.CharField(max_length=50, default="Lycée")

    formula = models.JSONField()
    intuition = models.JSONField()
    concepts_used = models.JSONField()
    raw_text = models.JSONField()  # OCR / Vision brut
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Exercise {self.id}"


class Solved(models.Model):

    STATUS_CHOICES = [
        ("not_started", "Not started"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
    ]

    state = models.CharField(max_length=20, choices=STATUS_CHOICES)
    score = models.IntegerField(default=0)
    attempts = models.IntegerField(default=0)

    exercise = models.ForeignKey(
        'Exercise',
        on_delete=models.CASCADE,
        related_name="progress"
    )

    student = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name="progress"
    )

    # 🔥 progression interne
    current_step = models.IntegerField(default=0)

    # 🔥 sauvegarde réponses (JSON)
    answers = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['exercise', 'student']

    def __str__(self):
        return f"student {self.student} {self.state} exercise {self.exercise.id}"


class Step(models.Model):
    exercise = models.ForeignKey(
        Exercise,
        related_name="steps",
        on_delete=models.CASCADE
    )

    step_number = models.PositiveIntegerField()
    objective = models.TextField()
    explanation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["step_number"]
        unique_together = ("exercise", "step_number")

    def __str__(self):
        return f"Step {self.step_number} - {self.exercise}"


class QCM(models.Model):
    step = models.OneToOneField(
        Step,
        related_name="qcm",
        on_delete=models.CASCADE
    )

    question = models.TextField()
    correct_choice = models.CharField(max_length=1)  # A, B, C, D

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QCM Step {self.step.step_number}"


class Choice(models.Model):
    qcm = models.ForeignKey(
        'QCM',
        related_name="choices",
        on_delete=models.CASCADE
    )

    label = models.CharField(max_length=1)  # A, B, C, D
    text = models.TextField()

    def __str__(self):
        return f"{self.label} - {self.text[:30]}"


class StudentAnswer(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    qcm = models.ForeignKey('QCM', on_delete=models.CASCADE)

    selected_choice = models.CharField(max_length=1)
    is_correct = models.BooleanField()

    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "qcm")
