from django.contrib import admin

from .models import Exercise, Attempt, StepAnswer, Mastery


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["__str__", "owner", "subject", "level", "generation_status", "created_at"]
    list_filter = ["generation_status", "subject", "level"]
    search_fields = ["title"]


class StepAnswerInline(admin.TabularInline):
    model = StepAnswer
    extra = 0


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "exercise", "mode", "score", "started_at", "finished_at"]
    list_filter = ["mode"]
    inlines = [StepAnswerInline]


@admin.register(Mastery)
class MasteryAdmin(admin.ModelAdmin):
    list_display = ["user", "chapter", "state", "score", "next_review_at"]
    list_filter = ["state"]
