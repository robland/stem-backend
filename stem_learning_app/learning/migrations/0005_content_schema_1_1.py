"""Contenu des parcours 1.0 → 1.1 : `answer.form` et `answer.source` des formula_input (« any » et null = comportement 1.0)."""

from django.db import migrations


def _set_form(content, form):
    for step in content.get("steps", []):
        activity = step.get("activity", {})
        if activity.get("type") != "formula_input":
            continue
        answer = activity.get("answer", {})
        if form is None:
            answer.pop("form", None)
            answer.pop("source", None)
        else:
            answer.setdefault("form", form)
            answer.setdefault("source", None)


def _migrate(apps, source, target, form):
    Exercise = apps.get_model("learning", "Exercise")
    for exercise in Exercise.objects.filter(schema_version=source).iterator():
        if exercise.content:
            _set_form(exercise.content, form)
            exercise.content["schema_version"] = target
        exercise.schema_version = target
        exercise.save(update_fields=["content", "schema_version"])


def forwards(apps, schema_editor):
    _migrate(apps, "1.0", "1.1", "any")


def backwards(apps, schema_editor):
    _migrate(apps, "1.1", "1.0", None)


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0004_attempt_progress"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
