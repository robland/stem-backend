from django.contrib import admin

from .models import Subject, Chapter


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "order"]


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "level", "order"]
    list_filter = ["subject", "level"]
    search_fields = ["name"]
