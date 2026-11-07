import importlib

import pytest
from django.apps import apps

from curriculum.models import Subject
from learning.models import Exercise
from llm.schemas import ExerciseContent
from llm.tests.factories import generated_exercise, step

pytestmark = pytest.mark.django_db

content_1_1 = importlib.import_module("learning.migrations.0005_content_schema_1_1")


def test_content_1_0_gets_formula_form(user):
    content = generated_exercise(step("s1"), step("s2", "mcq")) | {"schema_version": "1.0", "statement": "Énoncé $x$."}
    for field in ("form", "source"):
        del content["steps"][0]["activity"]["answer"][field]
    exercise = Exercise.objects.create(
        owner=user, subject=Subject.objects.get(code="maths"), level="3e", content=content, schema_version="1.0",
    )
    empty = Exercise.objects.create(owner=user, subject=Subject.objects.get(code="maths"), level="3e", schema_version="1.0")

    content_1_1.forwards(apps, None)

    exercise.refresh_from_db()
    assert exercise.schema_version == exercise.content["schema_version"] == "1.1"
    answer = exercise.content["steps"][0]["activity"]["answer"]
    assert (answer["form"], answer["source"]) == ("any", None)
    ExerciseContent.model_validate(exercise.content)
    empty.refresh_from_db()
    assert (empty.schema_version, empty.content) == ("1.1", {})

    content_1_1.backwards(apps, None)

    exercise.refresh_from_db()
    assert exercise.schema_version == "1.0"
    assert not {"form", "source"} & exercise.content["steps"][0]["activity"]["answer"].keys()
