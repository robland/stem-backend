from django.contrib import admin

from .models import Upload, ExtractedExercise


class ExtractedExerciseInline(admin.TabularInline):
    model = ExtractedExercise
    extra = 0
    fields = ["order", "subject", "chapter", "level", "validated_at"]


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "file_type", "status", "created_at"]
    list_filter = ["status", "file_type"]
    inlines = [ExtractedExerciseInline]


@admin.register(ExtractedExercise)
class ExtractedExerciseAdmin(admin.ModelAdmin):
    list_display = ["id", "upload", "order", "subject", "level", "validated_at"]
    list_filter = ["subject", "level"]
