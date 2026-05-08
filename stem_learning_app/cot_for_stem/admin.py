from django.contrib import admin
from .models import *
# Register your models here.


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    pass


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    pass


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ['id', 'step_number',  "qcm", 'created_at']
    list_filter = ['exercise',  "step_number",]


@admin.register(QCM)
class QCMAdmin(admin.ModelAdmin):
    pass


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    pass


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    pass


@admin.register(Solved)
class Admin(admin.ModelAdmin):
    pass

